---
trigger: always_on
---

# You have one SSOT for implementing paths

## When you decide to add a path to some python script or dockerfile, bash script, whatever. 

> Your SSOT is this script paths.py

> # IMPORTANT:
> do not write your custom paths in any other file or script.


# How to implement paths?

## Follow this steps:

### 1. Open at project root 'src/entsoe_pipeline/config/paths.py'

### 2. Read this file

### 3. Note existing constants 

> #### for example 'PROJECT_ROOT'

### 4. Import this file in your script

> #### for example 'from entsoe_pipeline import PROJECT_ROOT'

### 5. **(OPTIONAL)** If paths.py does not have constant you needed, add new constant to paths.py like:

> #### YOUR_UPPERCASE_CONSTANT_NAME = PROJECT_ROOT / "existing_in_reposetory_folder_name" / "another_folder_name_if_needed"

And add this constant to __all__ section in 'src/entsoe_pipeline/__init__.py'