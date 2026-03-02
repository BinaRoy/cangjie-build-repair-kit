# Git And Release Workflow

## Build product package

PowerShell:

```powershell
./scripts/build_release.ps1
```

Output:
- `release/product_bundle.zip` (recommended to share/upload)

## Git initialization (first time)

```powershell
git init
git add .
git commit -m "init: cangjie repair tool with product export"
```

## Connect remote and push

```powershell
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Update workflow

```powershell
# code changes
./scripts/build_release.ps1
git add .
git commit -m "feat: ..."
git push
```
