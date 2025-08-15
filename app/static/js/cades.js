// app/static/js/cades.js
const CADES = {
  CAPICOM_CURRENT_USER_STORE: 2,
  CAPICOM_LOCAL_MACHINE_STORE: 1,
  CAPICOM_STORE_OPEN_READ_ONLY: 0,
  CADESCOM_XML_SIGNATURE_TYPE_TEMPLATE: 2,
  SIG_METHOD: "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102012-gostr34112012-256",
  DIG_METHOD: "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34112012-256",
  SOAP11_NS: "http://schemas.xmlsoap.org/soap/envelope/",
  SOAP12_NS: "http://www.w3.org/2003/05/soap-envelope",
  WSU_NS: "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
};

function ensureBodyId(xml, id="Body-1"){
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, "text/xml");
  const body = doc.getElementsByTagNameNS(CADES.SOAP11_NS,"Body")[0] ||
               doc.getElementsByTagNameNS(CADES.SOAP12_NS,"Body")[0];
  if(!body) throw new Error("SOAP Body not found");
  if(!body.getAttributeNS(CADES.WSU_NS,"Id") && !body.getAttribute("wsu:Id")){
    body.setAttributeNS(CADES.WSU_NS, "wsu:Id", id);
    if(!doc.documentElement.getAttribute("xmlns:wsu")){
      doc.documentElement.setAttribute("xmlns:wsu", CADES.WSU_NS);
    }
  }
  return new XMLSerializer().serializeToString(doc);
}

async function listCertificates(includeMachine=true){
  if(!window.cadesplugin) { alert("Нужно расширение CryptoPro в браузере"); throw new Error("cadesplugin missing"); }
  const store = await cadesplugin.CreateObjectAsync("CAdESCOM.Store");
  await store.Open(CADES.CAPICOM_CURRENT_USER_STORE,"My",CADES.CAPICOM_STORE_OPEN_READ_ONLY);
  let certs = await store.Certificates;
  certs = await certs.Find(9); // time-valid
  const res = [];
  const n = await certs.Count;
  for(let i=1;i<=n;i++){
    const c = await certs.Item(i);
    res.push({Subject: await c.SubjectName, Thumbprint: await c.Thumbprint, Store: "CurrentUser"});
  }
  await store.Close();
  if(includeMachine){
    try{
      const s2 = await cadesplugin.CreateObjectAsync("CAdESCOM.Store");
      await s2.Open(CADES.CAPICOM_LOCAL_MACHINE_STORE,"My",CADES.CAPICOM_STORE_OPEN_READ_ONLY);
      let c2 = await s2.Certificates;
      c2 = await c2.Find(9);
      const m = await c2.Count;
      for(let i=1;i<=m;i++){
        const c = await c2.Item(i);
        res.push({Subject: await c.SubjectName, Thumbprint: await c.Thumbprint, Store: "LocalMachine"});
      }
      await s2.Close();
    }catch(e){ console.warn("LocalMachine store not accessible", e); }
  }
  return res;
}

async function signInBrowser(xml, thumbprint){
  if(!window.cadesplugin) { alert("Нужно расширение CryptoPro в браузере"); throw new Error("cadesplugin missing"); }
  const xml2 = ensureBodyId(xml, "Body-1");
  const sx = await cadesplugin.CreateObjectAsync("CAdESCOM.SignedXML");
  const signer = await cadesplugin.CreateObjectAsync("CAdESCOM.CPSigner");
  const store = await cadesplugin.CreateObjectAsync("CAdESCOM.Store");
  await store.Open(CADES.CAPICOM_CURRENT_USER_STORE, "My", CADES.CAPICOM_STORE_OPEN_READ_ONLY);
  let certs = await store.Certificates;
  certs = await certs.Find(0, thumbprint); // by SHA1
  if((await certs.Count) === 0){
    await store.Close();
    await store.Open(CADES.CAPICOM_LOCAL_MACHINE_STORE, "My", CADES.CAPICOM_STORE_OPEN_READ_ONLY);
    certs = await store.Certificates;
    certs = await certs.Find(0, thumbprint);
  }
  if((await certs.Count) === 0){
    await store.Close();
    throw new Error("Сертификат не найден");
  }
  const cert = await certs.Item(1);
  await store.Close();
  await signer.propset_Certificate(cert);
  await sx.propset_Content(xml2);
  await sx.propset_SignatureType(CADES.CADESCOM_XML_SIGNATURE_TYPE_TEMPLATE);
  await sx.propset_SignatureMethod(CADES.SIG_METHOD);
  await sx.propset_DigestMethod(CADES.DIG_METHOD);
  const tmpl =
`<Signature xmlns="http://www.w3.org/2000/09/xmldsig#" Id="SIG-1">
  <SignedInfo>
    <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
    <SignatureMethod Algorithm="${CADES.SIG_METHOD}"/>
    <Reference URI="#Body-1">
      <Transforms>
        <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
      </Transforms>
      <DigestMethod Algorithm="${CADES.DIG_METHOD}"/>
      <DigestValue></DigestValue>
    </Reference>
    <Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xades-props">
      <DigestMethod Algorithm="${CADES.DIG_METHOD}"/>
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
</Signature>`;
  await sx.propset_Signature(tmpl);
  return await sx.Sign(signer);
}

// UI bindings
async function uiCadesRefresh(){
  try{
    const list = await listCertificates(true);
    const sel = document.getElementById('cades_thumb');
    sel.innerHTML = "";
    list.forEach(c=>{
      const o = document.createElement('option');
      o.value = c.Thumbprint;
      o.textContent = `${c.Subject} [${c.Store}]`;
      sel.appendChild(o);
    });
    if(list.length===0){ alert("Сертификаты не найдены"); }
  }catch(e){
    alert("Ошибка: "+e);
  }
}

async function uiCadesSign(){
  const xml = document.getElementById('xml').value;
  const th = document.getElementById('cades_thumb').value;
  if(!xml || !th){ alert("XML и сертификат обязательны"); return; }
  try{
    const signed = await signInBrowser(xml, th);
    document.getElementById('signed').value = signed;
  }catch(e){
    alert("Ошибка подписи: "+e);
  }
}
