Title: Parameterizing Profile Handling

High-Level Instruction: The CIMXML serializer needs to handle any given CIM profile without relying on hardcoded logic for specific profiles. Modify the serializer to accept a profile URI as a parameter and use this URI to guide the serialization process.

Specific Code Changes:

1. Add a `profile_uri` argument to the `CIMXMLSerializer` constructor.
2. Modify the serializer logic to use the `profile_uri` when determining which CIM objects and attributes to serialize. This may require interacting with an external CIM profile definition or schema. 