# Part quantity in the design

A part can keep its quantity in the design file: give the Body an integer
property **Cantidad** (group *Fabricación*). `Quantity` and `NestingQuantity`
are read too.

- When the part is added to 1st Nesting, the Qty cell starts with that value
  (1 when the part has none).
- Changing Qty in the parts table writes the value back to the design part,
  creating the property if needed, so it is saved with the `.FCStd` file.
- Each preview copy records its source in the `SourceDocument` and
  `SourceObject` properties (group *1st Nesting*).

The `Cantidad_piezas.FCMacro` macro (Part Design toolbar *Fabricación*) asks
for a number and stores it on every selected part.
