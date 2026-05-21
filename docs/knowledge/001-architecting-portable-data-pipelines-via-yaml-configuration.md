# Architecting Portable Data Pipelines via YAML Configuration

Externalizing your configurations into a dedicated `config/` folder using YAML is an excellent architectural decision that demonstrates you are already thinking about scalability. In data engineering, keeping your business logic separate from your execution parameters is foundational. 

> "Code as configuration refers to a software design principle where configuration settings and parameters are stored as code separately from the executing code base".

By doing this, you ensure that your core transformation scripts in `src/entsoe/` remain immutable and completely unaware of whether they are running on your local machine, a staging server, or a massive production Kubernetes cluster. 

As a Senior Data Engineer, here are the fundamental design principles and practices I highly recommend you adopt as you build out this configuration-loading logic.

### 1. The "Why" Behind Parameterization
You are building an architecture where your data pipelines will inevitably need to run across multiple environments (Development, QA, Production). 

> "Parameterization confers the ability to separate code from its operating environment, enabling a single script to be performed across multiple platforms with simple parameter adjustments".

By loading `ports.yml` dynamically at runtime rather than hardcoding `8181` inside your Spark or Iceberg session builder, you make your code portable. If the infrastructure team decides to change the SeaweedFS port tomorrow, you simply update the YAML file without ever touching or risking bugs in your Python application logic. 

### 2. Designing the Python Module for Configuration
When you write the special Python script inside `src/entsoe/` to operate with your `config/` folder, be deliberate about how you name it and structure it. Do not just name it `utils.py` or `helpers.py`. 

> "Good module names are specific rather than generic: data_preprocessing_utils.py is better than utils.py". 

I recommend naming your script `config_loader.py` or `yaml_parser.py`. This immediately communicates its exact Single Responsibility to anyone reading your repository. Inside this file, you should build a configuration class or a set of loading functions that read the YAML files and return Python dictionaries or data classes.

### 3. Securely Parsing YAML in Python
When writing your parsing function, it is critical that you use safe methods to read the file. YAML files can theoretically embed arbitrary Python objects, which poses a severe security risk if you blindly evaluate them. 

> "It employs yaml.safe_load() to securely parse the YAML content into a Python dictionary". 

Always use `yaml.safe_load()` instead of the standard `yaml.load()`. Your loader function should look conceptually similar to this, gracefully handling file paths and returning the parsed dictionary:

```python
import yaml
from pathlib import Path

def load_yaml_config(file_name: str) -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / file_name
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
```

Additionally, remember that YAML is incredibly strict about whitespace. 

> "The syntax is very specific, but this serves as both a blessing and curse... you will find simple things like incorrect indentation will cause it to fail". 

Always enforce formatting standards using a linter in your CI/CD pipeline so that an accidental tab character in `ports.yml` doesn't crash your entire data pipeline in production.

### 4. Handling Secrets (The Danger of Plain Text)
Right now, you are storing port numbers in `ports.yml`, which is perfectly fine. However, as your project grows, you will inevitably need to store database passwords, API tokens, and AWS Secret Keys to connect to SeaweedFS or your Iceberg Catalog. **Do not put these in your YAML files.**

> "Be careful to not store any sensitive secrets in configuration files, which are typically stored in plain text". 
> "As per best practices, it is never a good idea to hardcode secrets within your pipelines and notebooks". 

If you commit plain-text passwords into version control via your YAML files, you are creating a massive security vulnerability. Instead, design your `config_loader.py` to recognize environment variables or to fetch secrets from a dedicated secrets manager (like Azure Key Vault, AWS Secrets Manager, or HashiCorp Vault) at runtime. Your Python script should merge the harmless configuration data from your YAML files with the highly sensitive secrets pulled securely from the environment. 

### 5. Adhere to the DRY Principle
As you build out more pipelines (for instance, scheduling them with Apache Airflow later), you will find that many different tasks require the exact same configuration parameters. 

> "For configuration that's shared across DAGs, we highly recommend specifying the configuration values in a single location, such as a shared YAML file, following the DRY (Don't Repeat Yourself) principle".

Do not create separate config files for every single script if they share common infrastructure variables. Having a unified `ports.yml` or `infrastructure.yml` means that if a connection parameter changes, you only update it in one place, guaranteeing that all downstream jobs inherit the correct, synchronized value.