**Model file:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<?iec61970-552 version="2.0"?> <rdf:RDF
xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
xmlns:cim="http://iec.ch/TC57/2013/CIM-schema-cim16#"
xmlns:md="http://iec.ch/TC57/61970-552/ModelDescription/1#"
xml:base="urn:uuid:">

<md:FullModel rdf:about="_[UUID]"> 
    <md:Model.created>[Date and time]</md:Model.created>
    <md:Model.description>[Description of the model]</md:Model.description>
    <md:Model.modelingAuthoritySet>[URI of the model source]</md:Model.modelingAuthoritySet>
    <md:Model.profile>http://iec.ch/TC57/2011/61970-452/Equipment/2/1</md:Model.profile>
    <md:Model.version>[Version number]</md:Model.version>
</md:FullModel>

</rdf:RDF>
```

**Hardcoded fields:**

* **`<?iec61970-552 version="2.0"?>`**: This field specifies the CIMXML version, which is 2.0 in this case. This should be hardcoded.
* **Namespaces (xmlns):** The namespaces for `rdf`, `cim`, and `md` should be hardcoded as these are standard and do not change.
* **`xml:base="urn:uuid:"`**: This field specifies the default namespace for all objects in the document. This should be hardcoded.
* **`md:Model.profile`**: This value should be hardcoded according to the profile you are using. In this example, "http://iec.ch/TC57/2011/61970-452/Equipment/2/1" is used. 

**Parameterized fields:**

* **`rdf:about="_[UUID]"`**: This field identifies the "FullModel" document itself. You should insert a unique UUID here.
* **`md:Model.created>[Date and time]`**: This field specifies the time when the model was created. You should insert the current date and time.
* **`md:Model.description>[Description of the model]`**: This field provides a short description of what the model contains.
* **`md:Model.modelingAuthoritySet>[URI of the model source]`**: This field specifies the source of the model data.
* **`md:Model.version>[Version number]`**: This field specifies the version of the model. You should insert an appropriate version number.

**Remember:**

* Replace `[UUID]` with an actual, unique UUID.
* Replace `[Date and time]`, `[Description of the model]`, `[URI of the model source]`, and `[Version number]` with the appropriate values. 