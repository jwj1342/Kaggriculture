# 数据归档与恢复

归档日期：**2026-10-01**。本页记录赛后数据迁移；最终比赛排名仍待官方公布。

**发布入口：[postmortem-2026-10-01](https://github.com/jwj1342/Kaggriculture/releases/tag/postmortem-2026-10-01)。**

**迁移已完成。** 13 份初始 Release 文件已回下载核对；D1 的 SQL 与 SQLite 分别恢复成功。
**2026-10-01 08:27:48 UTC**，项目 D1 已删除，官方列表确认目标不存在。
[下载与恢复验证](archive/RELEASE_VERIFICATION.json) · [Cloudflare 退役记录](archive/CLOUDFLARE_RETIREMENT.json)。

## 保留什么

| 资产 | 范围 |
| :--- | :--- |
| `arena-local.sqlite.zst` | 本地研究数据库：4,967,057 局、127 个 run、4,299 条 agent 记录 |
| `d1-kaggriculture.sqlite.zst` | Cloudflare D1 应用数据的独立可查询快照 |
| `d1-kaggriculture.sql.zst` | 官方完整应用表 SQL 导出，可独立重建 D1 数据 |
| `kaggriculture-archive-evidence.tar.gz` | 行数、schema、覆盖差异、完整性、压缩校验及导出/验证脚本 |
| `rl-line-archive-2026-09-29.tar.gz` | RL 线代码、实验资料和精简前的长篇研究记录 |
| `kaggriculture-final-artifacts.zip` | 两份原始最终提交 tar、源码、许可证、NOTICE、审查与结果摘要 |
| `kaggriculture-final-evidence.tar.gz` | 两份审批绑定的原报告、manifest、最终槽位判断及截止核对；不含全部原始分片 |
| `ALL_ASSETS_SHA256SUMS` / `ALL_ASSETS.json` | 初始 Release 全部归档资产的校验与范围清单 |
| `MIGRATION_COMPLETED.json` / `MIGRATION_SHA256SUMS` | 发布、回下载、恢复及退役的最终执行记录 |

D1 只含早期 **85,064 局 / 87 个 run**，远非当前全量数据库。它的这些对局逐字段核对后与本地对应记录一致，但 D1 还有本地没有的 **30,960 行 `matchups` 汇总表**，以及一条不同的历史 rating。
因此保留两份独立库，不用本地文件覆盖或代替远端历史。

本地库另含 2,451 条 `ladder_episodes`、48 条 `top_episodes`，以及运行和评级信息。它保存的是对局摘要和源码路径，并不内嵌全部策略源码、逐回合回放或所有评测分片。**下载数据库不等于拿到了重跑全部实验的全部输入。**

## 恢复到新文件

安装 `zstd` 和 SQLite CLI 后，下载 Release 资产并核对：

```bash
gh release download postmortem-2026-10-01 \
  --repo jwj1342/Kaggriculture --dir kaggriculture-archive
cd kaggriculture-archive
sha256sum -c ALL_ASSETS_SHA256SUMS
sha256sum -c MIGRATION_SHA256SUMS

zstd -d arena-local.sqlite.zst -o restored-arena.sqlite
zstd -d d1-kaggriculture.sqlite.zst -o restored-d1.sqlite
sqlite3 restored-arena.sqlite 'PRAGMA integrity_check;'
sqlite3 restored-d1.sqlite 'PRAGMA integrity_check;'
```

两次完整性检查都应返回 `ok`。保留原文件；在新路径打开和查询：

```bash
sqlite3 -readonly restored-arena.sqlite 'SELECT count(*) FROM episodes;'
KG_DB="$PWD/restored-arena.sqlite" python /path/to/Kaggriculture/tools/db.py stats
```

项目数据库工具可能启用 WAL 或初始化 schema；需要保留归档字节身份时，应先复制一份工作库再运行工具。
若要从官方 SQL 独立重建：

```bash
zstd -d d1-kaggriculture.sql.zst -o restored-d1.sql
sqlite3 recreated-d1.sqlite < restored-d1.sql
sqlite3 recreated-d1.sqlite 'PRAGMA integrity_check;'
```

SQL 导出保留五张应用表和索引。Cloudflare 官方导出不包含服务内部 `_cf_KV`，也不包含账号配置、凭据和 Time Travel 历史。
若以后重新启用 D1，应新建数据库、导入应用数据并使用新 ID。

## 验证与边界

- 通过只读 SQLite backup 生成本地快照；原 `data/arena.sqlite` 保留。
- 本地快照与 D1 恢复库分别执行完整 `integrity_check` 和外键检查。
- 按多重集保留重复/空键记录，逐行核对 D1 与本地覆盖，单独记录不同历史值。
- 每份压缩文件做解压后的完整 SHA-256 往返核验。
- 发布后回下载 13 份文件：11 项主体逐字节核 SHA，另两份完整清单核原文；作业 `23037729` 从下载文件独立恢复两种 D1 格式，完整性及全部表行数通过。
- 删除前第三次完整官方 SQL 导出与已发布原件一致，随后只删除准确名称/UUID 对应的 D1。
- SQLite backup 与原本地文件有 3 个头部字节差异，其余约 11 GB 数据逐字节一致；两者哈希分别保留，没有为追求相同哈希改写原库。
- RL 历史包检查了文件类型、路径、凭据/私密会话名称与已配置密钥字节；没有执行归档代码。

原独立备份审查在证据包中保留“未发布/未删除”的当时状态，实际迁移结果以本页及后续退役记录为准。

## Cloudflare 范围

本次仅处理项目 D1 **`kaggriculture`**，UUID `2ca54003-fb57-4eef-9dfd-83583fa3718a`。
Workers 列表为空；现有凭据没有列举 Pages/R2 的权限，也没有仓库配置确认其他资源属于此项目，因此未触及这些服务。

旧 `tools/d1.py` 查询、mirror 和向该数据库发布的功能现已停止；本地 SQLite、GitHub Release 和已提交的 Kaggle 策略不受影响。
旧 `tools/publish.sh --push` 的自动 D1 同步已移除；D1 工具也不再在项目名称缺失时选择另一个数据库。
历史协作文档中的“D1 当前镜像全部数据”描述已经过时。
