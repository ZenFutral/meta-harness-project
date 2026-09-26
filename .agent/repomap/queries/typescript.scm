;; Function & Method Declarations
(function_declaration
  name: (identifier) @name.definition.function
  parameters: (formal_parameters) @param
  return_type: (type_annotation)? @return)

(method_definition
  name: (property_identifier) @name.definition.function
  parameters: (formal_parameters) @param
  return_type: (type_annotation)? @return)

;; Class & Interface Declarations
(class_declaration
  name: (type_identifier) @name.definition.class
  heritage: (class_heritage)? @super_class)

(interface_declaration
  name: (type_identifier) @name.definition.class)

;; Imports & Exports
(import_statement
  source: (string) @import.module)

(export_statement
  source: (string)? @import.module)

(export_statement
  value: (asterisk_export) @export.wildcard)

;; Function Calls
(call_expression
  function: (identifier) @call.function)

(call_expression
  function: (member_expression
    property: (property_identifier) @call.method))
