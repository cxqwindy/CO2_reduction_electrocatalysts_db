# Partial DOI original-paper JSON data / 部分 DOI 原论文 JSON 数据

This directory contains a **partial collection of DOI-associated, parsed original-paper JSON files** used by this project. It is not a complete collection of the literature on CO2 electroreduction.

本目录保存本项目使用的**部分 DOI 及其对应原论文解析 JSON 文件**，并不代表 CO2 电催化还原领域的完整文献集合。

## Layout / 目录结构

```text
data/gold_data/<DOI prefix>/<DOI suffix>.json
```

For example, `data/gold_data/10.1016/j.example.2020.000001.json` corresponds to DOI `10.1016/j.example.2020.000001`.

例如，`data/gold_data/10.1016/j.example.2020.000001.json` 对应 DOI `10.1016/j.example.2020.000001`。

## Contents / 数据内容

At the time of this upload, the collection contains 424 JSON files. A record may contain the following fields:

- `title`: article title
- `authors`: article authors
- `emails`: author email addresses parsed from the source
- `abstract`: article abstract
- `referenceMentions`: in-text reference mentions
- `references`: parsed bibliography
- `source`, `year`, `createor`: source metadata
- `sections`: parsed section headings and original-paper text

本次上传共包含 424 个 JSON 文件。每条记录可能包括标题、作者、邮箱、摘要、引文、参考文献、来源、年份以及带章节标题的原论文正文。

## Copyright and data notice / 版权与数据说明

The JSON files are parsed representations of source articles. Copyright and other rights in the underlying article content remain with their respective authors and/or publishers. Inclusion in this repository does not grant a new license to the underlying papers. Users are responsible for verifying that their use and redistribution comply with the applicable article licenses, publisher terms, privacy requirements, and laws.

这些 JSON 是对来源论文的解析表示。底层论文内容的版权及其他权利仍归相应作者和/或出版社所有；收入本仓库不代表对原论文授予新的许可。使用者应自行确认使用与再分发行为符合对应论文许可、出版社条款、隐私要求及适用法律。
