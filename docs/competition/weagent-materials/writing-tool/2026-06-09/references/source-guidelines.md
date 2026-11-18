# Source Guidelines

Use this file as a compressed rule set. Do not quote or copy external guides into the user's document unless the user asks for citations.

## External Sources

- Google Developer Documentation Style Guide: https://developers.google.com/style
- Google style highlights: https://developers.google.com/style/highlights
- Google procedures guidance: https://developers.google.com/style/procedures
- Google code-in-text guidance: https://developers.google.com/style/code-in-text
- Microsoft Style Guide: https://learn.microsoft.com/en-us/style-guide/welcome/
- Microsoft step-by-step instructions: https://learn.microsoft.com/en-us/style-guide/procedures-instructions/writing-step-by-step-instructions
- Microsoft simple words and concise sentences: https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences
- Diataxis: https://diataxis.fr/
- The Good Docs Project templates: https://www.thegooddocsproject.dev/template

## Absorbed Rules

1. Be clear, concise, accessible, and globally understandable.
2. Use active voice and make the actor clear.
3. Put conditions before instructions.
4. Use numbered lists for procedures.
5. Use consistent, parallel headings.
6. Use descriptive links.
7. Put code-related text in code style.
8. Use bold for UI labels if the target document needs UI instructions.
9. Provide alt text or captions when adding images.
10. Keep procedures focused on actions the reader can execute.
11. Avoid unnecessary introductions that repeat the heading.
12. Keep sentences short and remove filler.

## User Rules

1. 先说结论，再给细节。
2. 每节只解决一个问题。
3. 步骤必须可执行，避免“显然、简单、容易”等主观词。
4. 参数、变量、文件名、命令、路径必须用代码格式。
5. 每个代码块前说明用途，代码块后说明输出或注意事项。
6. 不确定的信息必须标注 `待确认`，不能编造。
7. 中文为主，保留必要 English terminology。
8. 第一次出现术语时给出中文解释和 English original。
9. 公式、变量名、函数名保持原样。
10. 口吻正式、简洁，避免营销化表达。

## Chinese Technical Writing Rules

1. 简单、清晰、明了，不为了凑字数而堆字数。
2. 明确文档面向的读者和受众，使用他们能理解的词汇。
3. 提供必要信息，并按文档类型选择合适结构。
4. 使用排版、代码片段、架构图、UML、截图、参考资料辅助理解。
5. 先完成可用初稿，再像重构代码一样补全、删减、调整结构，最后补充图片和排版。

## Diataxis Use

- Tutorial: learning-oriented. Use when the reader needs a guided first success.
- How-to guide: task-oriented. Use when the reader needs to solve one concrete problem.
- Reference: information-oriented. Use when the reader needs exact APIs, configuration, commands, schemas, or limits.
- Explanation: understanding-oriented. Use when the reader needs architecture, decisions, tradeoffs, and context.

For a single technical document, combine these modes by section. Do not let one section try to be all four modes at once.
