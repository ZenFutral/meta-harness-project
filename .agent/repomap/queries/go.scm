;; Function & Method Declarations
(function_declaration
  name: (identifier) @name.definition.function
  parameters: (parameter_list) @param
  result: (parameter_list)? @return)

(method_declaration
  name: (field_identifier) @name.definition.function
  parameters: (parameter_list) @param
  result: (parameter_list)? @return)

;; Type Struct / Interface Declarations
(type_spec
  name: (type_identifier) @name.definition.class)

;; Import Declarations
(import_spec
  path: (interpreted_string_literal) @import.module)

;; Calls
(call_expression
  function: (identifier) @call.function)

(call_expression
  function: (selector_expression
    field: (field_identifier) @call.method))
