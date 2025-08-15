# app/signing/csp_sign.py
import pythoncom
from win32com.client import Dispatch
from lxml import etree

SIG_METHOD = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102012-gostr34112012-256"
DIG_METHOD = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34112012-256"

WSU_NS = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
SOAP11_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP12_NS = "http://www.w3.org/2003/05/soap-envelope"

CAPICOM_CURRENT_USER_STORE = 2
CAPICOM_LOCAL_MACHINE_STORE = 1
CAPICOM_STORE_OPEN_READ_ONLY = 0
CAPICOM_MY_STORE = "My"
CAPICOM_CERTIFICATE_FIND_TIME_VALID = 9
CAPICOM_CERTIFICATE_FIND_SHA1_HASH = 0

def _ensure_body_wsu_id(xml_bytes: bytes, body_id: str = "Body-1") -> bytes:
    root = etree.fromstring(xml_bytes)
    body = root.find(f".//{{{SOAP11_NS}}}Body") or root.find(f'.//{{{SOAP12_NS}}}Body')
    if body is None:
        raise ValueError("SOAP Body not found")
    if body.get(f"{{{WSU_NS}}}Id") is None and body.get("wsu:Id") is None:
        body.set(f"{{{WSU_NS}}}Id", body_id)
        if "wsu" not in (root.nsmap or {}):
            root.set("xmlns:wsu", WSU_NS)
    return etree.tostring(root, encoding="utf-8", xml_declaration=False)

def _store_open(location: int):
    store = Dispatch("CAdESCOM.Store")
    store.Open(location, CAPICOM_MY_STORE, CAPICOM_STORE_OPEN_READ_ONLY)
    return store

def _has_private_key(cert) -> bool:
    try:
        v = cert.HasPrivateKey
        try:
            return bool(v)
        except Exception:
            return bool(int(v))
    except Exception:
        try:
            return cert.PrivateKey is not None
        except Exception:
            return True

def list_certs(include_machine: bool = True, include_non_valid: bool = False, with_private_key_only: bool = True):
    pythoncom.CoInitialize()
    try:
        res = []
        for location, name in [(CAPICOM_CURRENT_USER_STORE, "CurrentUser"),
                               (CAPICOM_LOCAL_MACHINE_STORE, "LocalMachine")]:
            if (location == CAPICOM_LOCAL_MACHINE_STORE) and not include_machine:
                continue
            store = _store_open(location)
            certs = store.Certificates
            if not include_non_valid:
                certs = certs.Find(CAPICOM_CERTIFICATE_FIND_TIME_VALID)
            count = certs.Count
            for i in range(1, count+1):
                c = certs.Item(i)
                if with_private_key_only and not _has_private_key(c):
                    continue
                res.append({
                    "Subject": c.SubjectName,
                    "Thumbprint": c.Thumbprint,
                    "ValidFrom": str(c.ValidFromDate),
                    "ValidTo": str(c.ValidToDate),
                    "Store": name,
                    "HasPrivateKey": _has_private_key(c)
                })
            store.Close()
        return res
    finally:
        pythoncom.CoUninitialize()

def sign_xml_enveloped_on_body(xml_str: str, thumbprint_hex: str) -> str:
    pythoncom.CoInitialize()
    try:
        content = _ensure_body_wsu_id(xml_str.encode("utf-8"), "Body-1")
        tmpl = f'''<Signature xmlns="http://www.w3.org/2000/09/xmldsig#" Id="SIG-1">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
    <SignatureMethod Algorithm="{SIG_METHOD}"/>
    <Reference URI="#Body-1">
      <Transforms>
        <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
      </Transforms>
      <DigestMethod Algorithm="{DIG_METHOD}"/>
      <DigestValue></DigestValue>
    </Reference>
    <Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xades-props">
      <DigestMethod Algorithm="{DIG_METHOD}"/>
      <DigestValue></DigestValue>
    </Reference>
  </SignedInfo>
  <Object>
    <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="#SIG-1" Id="xades-props">
      <xades:SignedProperties>
        <xades:SignedSignatureProperties>
          <xades:SigningTime></xades:SigningTime>
          <xades:SigningCertificate/>
        </xades:SignedSignatureProperties>
      </xades:SignedProperties>
    </xades:QualifyingProperties>
  </Object>
</Signature>'''
        store = _store_open(CAPICOM_CURRENT_USER_STORE)
        certs = store.Certificates.Find(CAPICOM_CERTIFICATE_FIND_SHA1_HASH, thumbprint_hex)
        if certs.Count == 0:
            store.Close()
            store = _store_open(CAPICOM_LOCAL_MACHINE_STORE)
            certs = store.Certificates.Find(CAPICOM_CERTIFICATE_FIND_SHA1_HASH, thumbprint_hex)
        if certs.Count == 0:
            store.Close()
            raise RuntimeError("Certificate not found in CurrentUser\\My or LocalMachine\\My")
        cert = certs.Item(1)
        store.Close()

        signer = Dispatch("CAdESCOM.CPSigner")
        signer.Certificate = cert

        sx = Dispatch("CAdESCOM.SignedXML")
        sx.Content = content.decode("utf-8")
        sx.SignatureType = 2
        sx.SignatureMethod = SIG_METHOD
        sx.DigestMethod = DIG_METHOD
        sx.Signature = tmpl

        return sx.Sign(signer)
    finally:
        pythoncom.CoUninitialize()
