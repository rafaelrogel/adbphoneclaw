## Description: <br>
Caveman makes agent replies ultra-compressed by dropping filler while preserving technical terms, code blocks, and exact error messages. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[skaravind](https://clawhub.ai/user/skaravind) <br>

### License/Terms of Use: <br>
MIT-0 <br>


## Use Case: <br>
Developers use Caveman when they want terse agent answers, faster reading, and lower output-token use while preserving technical substance. It is intended for normal technical assistance, with a clear escape hatch for contexts that require more formal or nuanced wording. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: The terse response style can omit nuance that matters for legal, medical, security, formal, or high-stakes wording. <br>
Mitigation: Use normal mode or stop caveman when clarity, nuance, or formal output matters. <br>
Risk: The benchmark script can call the Anthropic API, read local environment settings, and write local benchmark results. <br>
Mitigation: Run the benchmark only intentionally, verify API credentials and environment settings first, and use dry-run mode when checking configuration. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/skaravind/caveman) <br>
- [Brevity Constraints Reverse Performance Hierarchies in Language Models](https://arxiv.org/abs/2604.00025) <br>
- [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, code, shell commands, guidance] <br>
**Output Format:** [Markdown text with unchanged code blocks and exact quoted error messages] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Terse response style; normal writing for code, git commits, and PR descriptions.] <br>

## Skill Version(s): <br>
1.0.2 (source: server release evidence) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
