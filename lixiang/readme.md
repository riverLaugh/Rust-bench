
## 项目概述

`expand_instance.py` 是一个 Python 脚本，用于对现有数据进行拓展。

---

## 环境要求

运行 `expand_instance.py` 前，请确保满足以下条件：

### 软件要求
- **Python**：版本 3.6 或更高。
- **Python 包**：
  - `datasets`：用于加载 Hugging Face 数据集。
  - `openai`：用于调用 OpenAI API。
  - `tqdm`：显示处理进度条。
  - `requests`

  安装命令：
  ```bash
  pip install datasets openai tqdm requests
  ```

### 其他要求
- **OpenAI API 密钥**：需要从 OpenAI 获取，用于生成错误报告和分类。
- **Hugging Face 数据集**：默认使用 `r1v3r/RustGPT_Bench_100`，需包含 `instance_id`、`code_snippet` 和 `test_patch` 字段。

---

## 设置步骤

1. **安装依赖项**  
   执行上述 `pip install` 命令安装所需库。

2. **配置 OpenAI API 密钥**  
   - 在 [OpenAI 平台](https://platform.openai.com/) 获取 API 密钥。
   - 设置环境变量：
     - Linux/Mac：
       ```bash
       export OPENAI_API_KEY='你的密钥'
       ```
3. **确认数据集访问**  
   确保可以访问目标数据集（默认 `r1v3r/RustGPT_Bench_100`），并验证其包含必要的字段。

---

## 使用方法

在命令行中运行脚本，基本语法如下：

```bash
python expand_instance.py --dataset_name_or_path <数据集名称或路径> --num_samples <样本数量> --split <数据集分割> --output_dir <输出目录>
```

### 参数说明
- **`--dataset_name_or_path`**  
  数据集名称或路径，默认：`r1v3r/RustGPT_Bench_100`。  
  示例：`r1v3r/RustGPT_Bench_100`

- **`--num_samples`**  
  拓展多少倍的数据集。如果是1，则拓展1倍。

- **`--split`**  
  处理的数据集分割，默认：`train`。  
  示例：`test`

- **`--output_dir`**  
  输出文件保存目录，默认：`./output`。  
  示例：`./results`

### 示例命令
```bash
python expand_instance.py --dataset_name_or_path r1v3r/RustGPT_Bench_100 --num_samples 2 --split train --output_dir ./output
```
此命令将：
- 处理 `r1v3r/RustGPT_Bench_100` 的 `train` 分割。
- 拓展两倍。
- 将结果保存到 `./output` 目录。

---

## 工作流程

1. **加载数据集**：从 Hugging Face 加载指定数据集。
2. **提取代码片段**：若无缓存，则调用 `transfer_dataset.py` 中的 `make_code_snippet` 函数提取代码。
3. **生成错误报告**：通过 OpenAI API 为每个代码片段生成错误报告。
4. **分类问题**：分析错误报告，标注问题类型、严重性及理由。
5. **保存结果**：将输出写入 `output_dir` 中的 `res.jsonl` 文件。

---

## 输出格式

输出文件为 `res.jsonl`，每行是一个 JSON 对象，示例结构如下：

```json
{
  "code_snippet": "Rust 代码片段",
  "target_function": "与代码片段相同",
  "review_type": "function",
  "issue_detail": {
    "problem_type": "逻辑错误",
    "location": "file_path: line: start-end",
    "level": "high",
    "description": "错误报告文本",
    "level_reason": "详细的中文分类理由（200-300 字）"
  },
  "repo": "仓库名称",
  "branch": "分支名称",
  "file_path": "file_path.rs",
  "language": "rust"
}
```

### 字段含义
- **`code_snippet`**：被分析的 Rust 代码。
- **`issue_detail.problem_type`**：问题类型，如“逻辑错误”。
- **`issue_detail.level`**：严重性（`low` 或 `high`）。
- **`issue_detail.level_reason`**：200-300 字的中文分类理由。

---

## 注意事项

- **API 费用**：使用 OpenAI API 会产生费用，尤其在处理大数据集时，请监控使用情况。
- **速率限制**：脚本使用多线程（错误报告最多 10 个 worker，推理最多 3 个），但可能需调整以适应 API 限制。
- **数据集兼容性**：确保数据集包含必要字段，否则需调整脚本。
- **错误处理**：脚本包含基本错误处理，生产环境可能需增强（如重试逻辑）。

---

## 相关脚本

### `transfer_dataset.py`
- **功能**：将数据集转换为 JSON 格式，提取代码片段及相关信息。
- **调用方式**：由 `expand_instance.py` 内部使用，也可独立运行：
  ```bash
  referenciaspython transfer_dataset.py --dataset_name r1v3r/RustGPT_Bench_100 --split train --output entries.json
  ```

---
