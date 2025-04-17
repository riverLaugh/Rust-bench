"""
SWE问题级别分析工具 - 增强版
功能：分析JSONL文件中各仓库的问题级别分布，生成专业可视化图表
"""

import json
import argparse
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import Dict, Tuple
import pandas as pd

# 配置参数
COLOR_SCHEME = {
    'low': '#2ecc71',   # 柔和的绿色
    'high': '#e74c3c'    # 醒目的红色
}
DEFAULT_OUTPUT = 'repo_level_distribution.html'

def load_and_analyze(file_path: str) -> Dict[str, Dict[str, int]]:
    """
    加载并分析数据文件
    
    参数:
        file_path (str): JSONL文件路径
        
    返回:
        Dict: 仓库统计数据 {repo: {'low': count, 'high': count}}
    """
    repo_stats = defaultdict(lambda: {'low': 0, 'high': 0})
    error_log = defaultdict(int)
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                sample = json.loads(line.strip())
                
                # 数据校验
                if 'repo' not in sample:
                    error_log['missing_repo'] += 1
                    continue
                    
                issue_detail = sample.get('issue_detail', {})
                level = str(issue_detail.get('level', '')).lower()
                
                if level not in {'low', 'high'}:
                    error_log[f'invalid_level_{level}'] += 1
                    continue
                
                repo = sample['repo']
                repo_stats[repo][level] += 1
                
            except (json.JSONDecodeError, KeyError) as e:
                error_log[f'parse_error_{type(e).__name__}'] += 1
                continue
    
    # 打印错误报告
    if error_log:
        print(f"\n[数据质量报告] 共发现 {sum(error_log.values())} 个问题:")
        for error, count in error_log.items():
            print(f"- {error}: {count}次")
    
    return dict(repo_stats)

def visualize_data(stats: Dict[str, Dict[str, int]], 
                  output_path: str = DEFAULT_OUTPUT,
                  figsize: Tuple[int, int] = (14, 7),
                  dpi: int = 200) -> None:
    """
    生成交互式可视化图表
    
    参数:
        stats (Dict): 仓库统计数据
        output_path (str): 输出文件路径
        figsize (Tuple): 图表尺寸
        dpi (int): 输出分辨率
    """
    # 转换数据格式
    df = pd.DataFrame.from_dict(stats, orient='index')
    df = df.reindex(columns=['high', 'low'])  # 确保排序
    
    # 创建绘图画布
    plt.figure(figsize=figsize, dpi=dpi)
    ax = df.plot.bar(
        stacked=False,
        color=[COLOR_SCHEME['high'], COLOR_SCHEME['low']],
        edgecolor='black',
        linewidth=0.8
    )
    
    # 样式配置
    ax.set_title('SWE问题级别分布分析', fontsize=16, pad=20, fontweight='bold')
    ax.set_xlabel('代码仓库', fontsize=12, labelpad=15)
    ax.set_ylabel('问题数量', fontsize=12, labelpad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 优化标签显示
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    
    # 添加数据标签
    for container in ax.containers:
        ax.bar_label(container, 
                    label_type='edge',
                    padding=3,
                    fmt='%d',
                    fontsize=9)
    
    # 添加图例
    ax.legend(
        title='问题级别',
        bbox_to_anchor=(1.02, 1),
        loc='upper left',
        borderaxespad=0.
    )
    
    # 保存输出
    output_format = output_path.split('.')[-1]
    save_kwargs = {
        'png': {'dpi': dpi, 'bbox_inches': 'tight'},
        'pdf': {'format': 'pdf', 'bbox_inches': 'tight'},
        'html': {'format': 'html'}
    }
    
    plt.tight_layout()
    plt.savefig(output_path, **save_kwargs.get(output_format, {}))
    print(f"\n图表已保存至: {output_path}")

def main():
    # 配置命令行参数
    parser = argparse.ArgumentParser(description='SWE问题级别分析工具')
    parser.add_argument('-i', '--input',default="/home/riv3r/SWE-bench/lixiang/siada_edu_case.jsonl" ,help='输入JSONL文件路径')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT, 
                       help='输出文件路径（支持.png/.pdf/.html）')
    parser.add_argument('--dpi', type=int, default=200, 
                       help='图片分辨率（仅限栅格格式）')
    args = parser.parse_args()
    
    # 执行分析流程
    stats = load_and_analyze(args.input)
    
    # 打印统计摘要
    summary = pd.DataFrame.from_dict(stats, orient='index')
    print("\n[统计摘要]")
    print(summary.describe())
    print("\n[详细统计]")
    print(summary)
    
    # 生成可视化结果
    visualize_data(stats, args.output, dpi=args.dpi)

if __name__ == '__main__':
    main()