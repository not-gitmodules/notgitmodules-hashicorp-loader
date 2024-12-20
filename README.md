# HashiCorp Loader Module

---

# Usage

With `not_gitmodules`:


```yaml
# notgitmodules.yaml

utils:
  hashicorp_loader: https://github.com/Armen-Jean-Andreasian/notgitmodules-hashicorp-loader

```

---
Snippet:

```python
from utlis.hashicorp_loader import HashiCorpLoader


HashiCorpLoader.load()
```