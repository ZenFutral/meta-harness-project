;; Function & Async Function Declarations
(function_definition
  name: (identifier) @name.definition.function
  parameters: (parameters) @param
  return_type: (type)? @return
  body: (block
    (expression_statement
      (string))? @docstring))

;; Class Declarations & Superclasses
(class_definition
  name: (identifier) @name.definition.class
  superclasses: (argument_list)? @super_class
  body: (block
    (expression_statement
      (string))? @docstring))

;; Import Statements
(import_statement
  name: (dotted_name) @import.module)

(import_from_statement
  module_name: (dotted_name)? @import.module
  name: (dotted_name) @import.symbol)

(import_from_statement
  module_name: (dotted_name)? @import.module
  name: (wildcard_import) @export.wildcard)

;; Function & Method Calls
(call
  function: (identifier) @call.function)

(call
  function: (attribute
    attribute: (identifier) @call.method))
