# app/routers/api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.config import settings
from lxml import etree
import requests

router = APIRouter()

# ---------- Builders ----------
class ExportIn(BaseModel):
    ogrn: str = Field(..., min_length=5, max_length=20)
    version: str = "10.0.2.1"

@router.post("/build/export-org-registry", response_class=str)
def build_export_org_registry(data: ExportIn):
    from datetime import datetime
    import uuid
    current_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+09:00"
    message_guid = str(uuid.uuid4())
    xml = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:base="http://dom.gosuslugi.ru/schema/integration/base/"
                  xmlns:org="http://dom.gosuslugi.ru/schema/integration/organizations-registry-common/"
                  xmlns:xd="http://www.w3.org/2000/09/xmldsig#"
                  xmlns:org1="http://dom.gosuslugi.ru/schema/integration/organizations-base/"
                  xmlns:org2="http://dom.gosuslugi.ru/schema/integration/organizations-registry-base/">
   <soapenv:Header>
      <base:ISRequestHeader>
         <base:Date>{current_date}</base:Date>
         <base:MessageGUID>{message_guid}</base:MessageGUID>
      </base:ISRequestHeader>
   </soapenv:Header>
   <soapenv:Body>
      <org:exportOrgRegistryRequest Id="foo" base:version="{data.version}">
         <org:SearchCriteria>
            <org1:OGRN>{data.ogrn}</org1:OGRN>
         </org:SearchCriteria>
      </org:exportOrgRegistryRequest>
   </soapenv:Body>
</soapenv:Envelope>'''
    return xml

# ---------- Transport ----------
class SendIn(BaseModel):
    endpoint_path: str = Field(..., min_length=2)
    xml: str = Field(..., min_length=10)
    soap11: bool | None = None
    soap_action: str | None = None

@router.post("/send", response_class=str)
def send(data: SendIn):
    soap11 = settings.soap11 if data.soap11 is None else data.soap11
    path = data.endpoint_path if data.endpoint_path.startswith("/") else "/" + data.endpoint_path
    url = f"http://{settings.stunnel_host}:{settings.stunnel_port}{path}"
    headers = {
        "Host": settings.target_host,
        "Connection": "close",
        "Content-Type": "text/xml; charset=utf-8" if soap11 else "application/soap+xml; charset=utf-8"
    }
    if soap11 and data.soap_action:
        headers["SOAPAction"] = data.soap_action
    try:
        r = requests.post(url, data=data.xml.encode("utf-8"), headers=headers, timeout=60)
        return r.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# ---------- Server-side signing (optional) ----------
class SignIn(BaseModel):
    xml: str = Field(..., min_length=10)
    thumbprint: str = Field(..., min_length=10)

@router.post("/sign/server", response_class=str)
def sign_server(data: SignIn):
    try:
        from app.signing import csp_sign
        return csp_sign.sign_xml_enveloped_on_body(data.xml, data.thumbprint.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Certificates list (optional, server-side) ----------
@router.get("/certs")
def certs(include_machine: bool = True, include_non_valid: bool = False, with_private_key_only: bool = True):
    try:
        from app.signing import csp_sign
        return csp_sign.list_certs(include_machine=include_machine, include_non_valid=include_non_valid, with_private_key_only=with_private_key_only)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
