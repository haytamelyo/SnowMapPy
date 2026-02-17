# SnowMapPy Deployment Guide

## Pre-Deployment Checklist

### For Lead Developer (Haytam)

Before deploying to PyPI and GitHub Pages:

1. **Version Check**: Confirm version is `1.0.0` across all files
   ```bash
   grep -r "1.0.0" --include="*.py" --include="*.toml"
   ```

2. **Run Tests**: Ensure all functionality works
   ```bash
   python -c "from SnowMapPy import process_modis_ndsi_cloud; print('OK')"
   ```

3. **Build Documentation Locally**
   ```bash
   pip install -r requirements-docs.txt
   python -m mkdocs serve
   ```

---

## Partner Testing Workflow

### For Hatim and Mostafa

#### Option 1: Clone and Test Locally (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 3. Install package in development mode
pip install -e .

# 4. Test the package
python -c "from SnowMapPy import process_modis_ndsi_cloud; print('SUCCESS')"
snowmappy --version

# 5. Preview documentation locally
pip install -r requirements-docs.txt
python -m mkdocs serve
# Open http://127.0.0.1:8000 in browser
```

#### Option 2: Install Test PyPI Version

After publishing to Test PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ SnowMapPy
```

---

## PyPI Deployment Steps

### 1. Prepare for Release

```bash
# Ensure you're in the project root
cd SnowMapPy

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Install build tools
pip install build twine
```

### 2. Build the Package

```bash
python -m build
```

This creates:
- `dist/SnowMapPy-1.0.0.tar.gz` (source distribution)
- `dist/SnowMapPy-1.0.0-py3-none-any.whl` (wheel)

### 3. Test on Test PyPI First

```bash
# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ SnowMapPy
```

### 4. Deploy to Production PyPI

```bash
# Upload to PyPI (requires PyPI API token)
python -m twine upload dist/*
```

**PyPI Credentials**: Use API tokens, not passwords.
- Create at: https://pypi.org/manage/account/token/
- Store in `~/.pypirc`:
  ```ini
  [pypi]
  username = __token__
  password = pypi-xxxxxxxxxxxxxxxx
  ```

---

## Documentation Deployment

### Automatic (GitHub Actions)

Documentation deploys automatically when you push to `main`:

1. Push to GitHub → GitHub Actions triggers
2. Builds MkDocs site
3. Deploys to `gh-pages` branch
4. Available at: `https://haytamelyo.github.io/SnowMapPy`

### Enable GitHub Pages

1. Go to repository **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `gh-pages` / `/ (root)`
4. Save

### Manual Deployment (if needed)

```bash
python -m mkdocs gh-deploy --force
```

---

## Repository Structure for Deployment

```
SnowMapPy/
├── .github/
│   └── workflows/
│       └── docs.yml          # Auto-deploy docs to GitHub Pages
├── docs/                     # Documentation source
├── SnowMapPy/                # Package source
├── pyproject.toml            # Package metadata
├── MANIFEST.in               # PyPI include rules
├── requirements.txt          # Dependencies
├── requirements-docs.txt     # Documentation dependencies
├── README.md                 # PyPI/GitHub readme
└── LICENSE                   # MIT license
```

---

## Files NOT Included in PyPI Package

These are excluded by `.gitignore` and `MANIFEST.in`:

- `*.ipynb` - Jupyter notebooks
- `*.nbc`, `*.nbi` - Numba cache files
- `__pycache__/` - Python cache
- `docs/` - Documentation (not needed for pip install)
- `site/` - Built documentation
- `.github/` - GitHub-specific files

---

## Post-Deployment Verification

### Test PyPI Installation

```bash
pip install SnowMapPy
python -c "import SnowMapPy; print(SnowMapPy.__version__)"
# Should print: 1.0.0
```

### Test CLI

```bash
snowmappy --version
# Should print: SnowMapPy v1.0.0
```

### Test Documentation

- Visit: https://haytamelyo.github.io/SnowMapPy
- Check all navigation links work
- Verify code examples display correctly

---

## Quick Reference Commands

| Action | Command |
|--------|---------|
| Build package | `python -m build` |
| Upload to Test PyPI | `twine upload --repository testpypi dist/*` |
| Upload to PyPI | `twine upload dist/*` |
| Preview docs | `python -m mkdocs serve` |
| Deploy docs | `python -m mkdocs gh-deploy` |
| Install local | `pip install -e .` |

---

## Authors

- **Haytam Elyoussfi** - haytam.elyoussfi@um6p.ma
- **Hatim Bechri** - hatim.bechri@uqtr.ca
- **Mostafa Bousbaa** - Mostafa.bousbaa@um6p.ma
