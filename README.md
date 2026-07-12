# SiYuan Codex Skills

这是一个公开归档仓库，收录从个人 Codex 配置仓库整理出的两个通用 SiYuan skills。公开版不包含个人分类、真实 ID、私人模板或一次性清理流程。

## 包含的 skills

- `siyuan-cli`：通过本地 `siyuan` CLI 搜索、读取、创建、导入、导出和管理思源笔记。
- `siyuan-to-obsidian-migration`：将显式选择的思源 notebook 迁移到 Obsidian，并通用修复附件、wikilink、嵌入和列表缩进。

## 安装

将需要的 skill 目录复制到 `$HOME/.agents/skills/`：

```bash
git clone https://github.com/CamusZ11/siyuan-codex-skills.git
cp -R siyuan-codex-skills/siyuan-cli "$HOME/.agents/skills/"
cp -R siyuan-codex-skills/siyuan-to-obsidian-migration "$HOME/.agents/skills/"
```

## 本地配置

确保 `siyuan` 可执行文件位于 `PATH`，并按需设置：

```bash
export SIYUAN_WORKSPACE="$HOME/SiYuan"
export OBSIDIAN_VAULT="$HOME/ObsidianVault"
```

迁移脚本默认 dry-run，只有显式 `--write` 才会写入。每个 notebook 映射必须指向 vault 内的相对子目录；绝对路径、`.`、`..`、vault 根目录和解析后逃逸的路径会在删除或写入前被拒绝。

通用映射示例：

```bash
python3 siyuan-to-obsidian-migration/scripts/migrate_siyuan_to_obsidian.py \
  --notebook '<notebook-id>=source-notebook/target-folder'
```

本仓库不包含 LICENSE；使用前请自行确认这些归档内容是否符合你的场景和合规要求。
