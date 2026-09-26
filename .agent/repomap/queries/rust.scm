;; Function Declarations
(function_item
  name: (identifier) @name.definition.function
  parameters: (parameters) @param
  return_type: (type)? @return)

;; Struct, Enum, Trait Declarations
(struct_item
  name: (type_identifier) @name.definition.class)

(enum_item
  name: (type_identifier) @name.definition.class)

(trait_item
  name: (type_identifier) @name.definition.class)

;; Use / Import Statements
(use_declaration
  argument: (scoped_identifier) @import.module)

(use_declaration
  argument: (use_wildcard) @export.wildcard)

;; Calls
(call_expression
  function: (identifier) @call.function)

(method_call_expression
  name: (field_identifier) @call.method)
