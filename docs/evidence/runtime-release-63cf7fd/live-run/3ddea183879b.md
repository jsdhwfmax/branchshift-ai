# BranchShift evidence report: 3ddea183879b

Live provider record.

Deterministic summary of stored evidence. No model generated this explanation, and this export did not replay checks or independently authenticate provider records.
The JSON report remains the full machine-readable record. Durations below are rounded to three decimal places.

Stored live winner and clean-revalidation evidence satisfy the reporting gates.

| Field | Recorded value |
| --- | --- |
| Run status | completed |
| Failure reason | Unknown (not recorded) |
| Repository | https://github\.com/jsdhwfmax/branchshift\-ai |
| Project directory | Unknown (not recorded) |
| Target | pydantic\-v2 |
| Created | 2026\-09\-10T06:37:39\.829215\+00:00 |
| Last saved | 2026\-09\-10T06:39:13\.051098\+00:00 |
| Exact model ID | nvidia/Nemotron\-3\-Ultra\-550b\-a55b |
| Orchestrator revision | 63cf7fdb4c62e119facb87fe108e9c278960a5c1 |
| Orchestrator content digest | b10f14ba54cb60d5f1c858eb6928d4957255409f4e689d21b187e8d83fe07c1b |
| Orchestrator dirty checkout | Yes |
| Runtime-config digest | 99c4a77f36522aaf6cc6830ab6f0f40f45ab95066077dda61cf4ad75a81a7b8e |
| Baseline commit | 63cf7fdb4c62e119facb87fe108e9c278960a5c1 |
| Baseline checkpoint | c605be9f\-2d6a\-4c71\-b897\-f7ca3e5635b2 |
| Baseline collected tests | 13 |
| Baseline test-contract digest | 425a9c3c2f3a1a564707e77d054b359cf5e4459f59d9c2fa38cdeceed616948f |
| Stored winner ID | minimal |
| Stored patch SHA-256 | d3bf63ae2cd146b4db54564aa0dc4b20c3931e1dbbba63954e3fcc62f4a5b009 |

## Recorded selection

Selection order: patch-applicable candidates; prefer the recorded passed-candidate pool; then higher test pass ratio, dependency consistency, fewer lint findings, fewer changed lines, shorter elapsed time, and strategy ID.

Recorded winner: minimal.

minimal versus compatibility: changed lines is 44 versus 71; this supports the stored selection.
minimal versus refactor: the other candidate did not meet the passed-candidate gate.

## Candidate evidence

### minimal

| Field | Recorded value |
| --- | --- |
| Status | passed |
| Tests collected | 13 |
| Tests passed | 13 |
| Tests failed / collection errors | 0 |
| Dependency consistency | Yes |
| Lint findings | 1 |
| Changed files | 3 |
| Changed lines | 44 |
| Elapsed seconds | 7.882 |
| Patch applicable | Yes |
| Pydantic major | 2 |
| Test exit code | 0 |
| Dependency exit code | 0 |
| Test contract preserved | Yes |
| Child checkpoint | 38a6d383\-4ae3\-41bb\-81a7\-8a56202f0f1f |
| Failure reason | Unknown (not recorded) |
| Diagnostics | \.\.\.\.\.\.\.\.\.\.\.\.\.                                                            \[100%\] ↵ 13 passed, 25 warnings in 0\.10s ↵ UP045 \[\*\] Use \`X \| None\` for type annotations ↵   \-\-&gt; src/sample\_app/models\.py:11:15 ↵    \| ↵  9 \|     name: str ↵ 10 \|     email: str ↵ 11 \|     nickname: Optional\[str\] = None ↵    \|               ^^^^^^^^^^^^^ ↵ 12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\) ↵    \| ↵ help: Convert to \`X \| None\` ↵    \| ↵ 10 \|     email: str ↵    \-     nickname: Optional\[str\] = None ↵ 11 \+     nickname: str \| None = None ↵ 12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\) ↵    \| ↵  ↵ Found 1 error\. ↵ \[\*\] 1 fixable with the \`\-\-fix\` option\. |

### compatibility

| Field | Recorded value |
| --- | --- |
| Status | passed |
| Tests collected | 13 |
| Tests passed | 13 |
| Tests failed / collection errors | 0 |
| Dependency consistency | Yes |
| Lint findings | 1 |
| Changed files | 2 |
| Changed lines | 71 |
| Elapsed seconds | 15.694 |
| Patch applicable | Yes |
| Pydantic major | 2 |
| Test exit code | 0 |
| Dependency exit code | 0 |
| Test contract preserved | Yes |
| Child checkpoint | 6292762c\-373d\-4fbe\-ad9f\-fc557dc5f356 |
| Failure reason | Unknown (not recorded) |
| Diagnostics | \.\.\.\.\.\.\.\.\.\.\.\.\.                                                            \[100%\] ↵ 13 passed, 14 warnings in 0\.10s ↵ F401 \[\*\] \`typing\.Optional\` imported but unused ↵  \-\-&gt; src/sample\_app/models\.py:2:20 ↵   \| ↵ 1 \| from datetime import datetime ↵ 2 \| from typing import Optional ↵   \|                    ^^^^^^^^ ↵ 3 \| ↵ 4 \| from pydantic import BaseModel, Field, field\_validator, model\_validator ↵   \| ↵ help: Remove unused import: \`typing\.Optional\` ↵   \| ↵ 1 \| from datetime import datetime ↵   \- from typing import Optional ↵ 2 \| ↵   \| ↵  ↵ Found 1 error\. ↵ \[\*\] 1 fixable with the \`\-\-fix\` option\. |

### refactor

| Field | Recorded value |
| --- | --- |
| Status | failed |
| Tests collected | 13 |
| Tests passed | 11 |
| Tests failed / collection errors | 2 |
| Dependency consistency | Yes |
| Lint findings | 1 |
| Changed files | 3 |
| Changed lines | 58 |
| Elapsed seconds | 23.227 |
| Patch applicable | Yes |
| Pydantic major | 2 |
| Test exit code | 1 |
| Dependency exit code | 0 |
| Test contract preserved | Yes |
| Child checkpoint | dcef0c62\-9ba9\-40e6\-b9e7\-70a9aaa215c4 |
| Failure reason | Test execution failed; inspect the test diagnostic |
| Diagnostics | Validation failed\. Repair only the declared files\. tests=11/13, pip\_check=True, lint\_findings=1, pydantic\_major=2, reason=Test execution failed; inspect the test diagnostic\. ↵ Test failure — tests\.test\_api::test\_dict\_boundary: AssertionError: assert \{&\#x27;user\_id&\#x27;: 3\.\.\.39, 5, 96088\)\} == \{&\#x27;id&\#x27;: 3, &\#x27;na\.\.\.39, 5, 96088\)\} ↵    ↵   Omitting 3 identical items, use \-vv to show ↵   Left contains 1 more item: ↵   \{&\#x27;user\_id&\#x27;: 3\} ↵   Right contains 1 more item: ↵   \{&\#x27;id&\#x27;: 3\} ↵   Use \-v to get more diff ↵ Test failure — tests\.test\_models::test\_alias\_is\_used\_during\_serialization: KeyError: &\#x27;id&\#x27; ↵ \.F\.\.\.\.\.\.\.\.F\.\.                                                            \[100%\] ↵ =================================== FAILURES =================================== ↵ \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ test\_dict\_boundary \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ ↵ tests/test\_api\.py:10: in test\_dict\_boundary ↵     assert payload == \{&quot;id&quot;: 3, &quot;name&quot;: &quot;Lin&quot;, &quot;email&quot;: &quot;l@e\.com&quot;, &quot;created\_at&quot;: payload\[&quot;created\_at&quot;\]\} ↵ E   AssertionError: assert \{&\#x27;user\_id&\#x27;: 3\.\.\.39, 5, 96088\)\} == \{&\#x27;id&\#x27;: 3, &\#x27;na\.\.\.39, 5, 96088\)\} ↵ E      ↵ E     Omitting 3 identical items, use \-vv to show ↵ E     Left contains 1 more item: ↵ E     \{&\#x27;user\_id&\#x27;: 3\} ↵ E     Right contains 1 more item: ↵ E     \{&\#x27;id&\#x27;: 3\} ↵ E     Use \-v to get more diff ↵ \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ test\_alias\_is\_used\_during\_serialization \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ ↵ tests/test\_models\.py:45: in test\_alias\_is\_used\_during\_serialization ↵     assert payload\[&quot;id&quot;\] == 7 and &quot;user\_id&quot; not in payload ↵            ^^^^^^^^^^^^^ ↵ E   KeyError: &\#x27;id&\#x27; ↵ =========================== short test summary info ============================ ↵ FAILED tests/test\_api\.py::test\_dict\_boundary \- AssertionError: assert \{&\#x27;user\_\.\.\. ↵ FAILED tests/test\_models\.py::test\_alias\_is\_used\_during\_serialization \- KeyErr\.\.\. ↵ 2 failed, 11 passed, 25 warnings in 0\.11s ↵ F401 \[\*\] \`typing\.Optional\` imported but unused ↵  \-\-&gt; src/sample\_app/models\.py:2:20 ↵   \| ↵ 1 \| from datetime import datetime ↵ 2 \| from typing import Optional ↵   \|                    ^^^^^^^^ ↵ 3 \| ↵ 4 \| from pydantic import BaseModel, Field, ValidationInfo, field\_validator, model\_validator ↵   \| ↵ help: Remove unused import: \`typing\.Optional\` ↵   \| ↵ 1 \| from datetime import datetime ↵   \- from typing import Optional ↵ 2 \| ↵   \| ↵  ↵ Found 1 error\. ↵ \[\*\] 1 fixable with the \`\-\-fix\` option\. |

## Clean-baseline revalidation

Matching clean-revalidation evidence is recorded.

| Field | Recorded value |
| --- | --- |
| Revalidation checkpoint ID | 5dbfadb5\-0005\-46db\-8413\-79522a22d8f3 |
| Status | passed |
| Tests collected | 13 |
| Tests passed | 13 |
| Tests failed | 0 |
| Pydantic major | 2 |
| Test contract preserved | Yes |
| Test exit code | 0 |
| Dependency exit code | 0 |
| Dependency consistency | Yes |
| Failure reason | Unknown (not recorded) |
| Diagnostics | \.\.\.\.\.\.\.\.\.\.\.\.\.                                                            \[100%\] ↵ 13 passed, 25 warnings in 0\.10s ↵ UP045 \[\*\] Use \`X \| None\` for type annotations ↵   \-\-&gt; src/sample\_app/models\.py:11:15 ↵    \| ↵  9 \|     name: str ↵ 10 \|     email: str ↵ 11 \|     nickname: Optional\[str\] = None ↵    \|               ^^^^^^^^^^^^^ ↵ 12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\) ↵    \| ↵ help: Convert to \`X \| None\` ↵    \| ↵ 10 \|     email: str ↵    \-     nickname: Optional\[str\] = None ↵ 11 \+     nickname: str \| None = None ↵ 12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\) ↵    \| ↵  ↵ Found 1 error\. ↵ \[\*\] 1 fixable with the \`\-\-fix\` option\. |

## Retained citations

- @validator and @root\_validator are deprecated — https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#validator\-and\-root\_validator\-are\-deprecated
  @validator and @root\_validator are deprecated @validator has been deprecated, and should be replaced with @field\_validator , which provides various new features and improvements\. The new @field\_validator decorator does not have the each\_item keyword argument; validators you want to apply to items within a generic container should be added by annotating the type argument\. See validators in Annotated metadata for details\. This looks like list\[Annotated\[int, Field\(ge=0\)\]\] Even if you keep using the deprecated @validator decorator, you can no longer add the field or config arguments to the signature of validator functions\. If you need access to these, you’ll need to migrate to @field\_validator — see the next section for more details\. If you use the always=True keyword argument to a validator function, note that standard validators for the annotated type will also be applied even to defaults, not just the custom validators\. For example, despite the fact that the validator below will never error, the following code raises a ValidationError : from pydantic import BaseModel, validator class Model\(BaseModel\): x: str = 1 @validator\(&\#x27;x&\#x27;, always=True\) @classmethod def validate\_x\(cls, v\): return v Model\(\) @root\_validator has been deprecated, and should be replaced with @model\_validator , which also provides new features and improvements\. Be aware that the allowed signatures have changed \(see the relevant documentation \)\. Under some circumstances \(such as assignment when model\_config\[&\#x27;validate\_assignment&\#x27;\] is True \), the @model\_validator decorator will receive an instance of the model, not a dict of values\. You may need to be careful to handle this case\. Even if you keep using the deprecated @root\_validator decorator, due to refactors in validation logic, you can no longer run with skip\_on\_failure=False \(which is the default value of this keyword argument, so must be set explicitly to True \)\.
- Changes to config — https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-config
  Changes to config In Pydantic V2, to specify config on a model, you should set a class attribute called model\_config to be a dict with the key/value pairs you want to be used as the config\. The Pydantic V1 behavior to create a class called Config in the namespace of the parent BaseModel subclass is now deprecated\. When subclassing a model, the model\_config attribute is inherited\. This is helpful in the case where you’d like to use a base class with a given configuration for many models\. Note, if you inherit from multiple BaseModel subclasses, like class MyModel\(Model1, Model2\) , the non\-default settings in the model\_config attribute from the two models will be merged, and for any settings defined in both, those from Model2 will override those from Model1 \. The following config settings have been removed: allow\_mutation — this has been removed\. You should be able to use frozen equivalently \(inverse of current use\)\. error\_msg\_templates fields — this was the source of various bugs, so has been removed\. You should be able to use Annotated on fields to modify them as desired\. getter\_dict — orm\_mode has been removed, and this implementation detail is no longer necessary\. smart\_union \- the default union\_mode in Pydantic V2 is &\#x27;smart&\#x27; \. underscore\_attrs\_are\_private — the Pydantic V2 behavior is now the same as if this was always set to True in Pydantic V1\. json\_loads json\_dumps copy\_on\_model\_validation post\_init\_call The following config settings have been renamed: allow\_population\_by\_field\_name → populate\_by\_name \(or validate\_by\_name starting in v2\.11\) anystr\_lower → str\_to\_lower anystr\_strip\_whitespace → str\_strip\_whitespace anystr\_upper → str\_to\_upper keep\_untouched → ignored\_types max\_anystr\_length → str\_max\_length min\_anystr\_length → str\_min\_length orm\_mode → from\_attributes schema\_extra → json\_schema\_extra validate\_all → validate\_default See the ConfigDict API reference for more details\.
- Changes to pydantic\.BaseModel — https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-pydanticbasemodel
  Changes to pydantic\.BaseModel Various method names have been changed; all non\-deprecated BaseModel methods now have names matching either the format model\_\.\* or \_\_\.\*pydantic\.\*\_\_ \. Where possible, we have retained the deprecated methods with their old names to help ease migration, but calling them will emit DeprecationWarning s\. Pydantic V1 Pydantic V2 \_\_fields\_\_ model\_fields \_\_private\_attributes\_\_ \_\_pydantic\_private\_\_ \_\_validators\_\_ \_\_pydantic\_validator\_\_ construct\(\) model\_construct\(\) copy\(\) model\_copy\(\) dict\(\) model\_dump\(\) json\_schema\(\) model\_json\_schema\(\) json\(\) model\_dump\_json\(\) parse\_obj\(\) model\_validate\(\) update\_forward\_refs\(\) model\_rebuild\(\) Some of the built\-in data\-loading functionality has been slated for removal\. In particular, parse\_raw and parse\_file are now deprecated\. In Pydantic V2, model\_validate\_json works like parse\_raw \. Otherwise, you should load the data and then pass it to model\_validate \. The from\_orm method has been deprecated; you can now just use model\_validate \(equivalent to parse\_obj from Pydantic V1\) to achieve something similar, as long as you’ve set from\_attributes=True in the model config\. The \_\_eq\_\_ method has changed for models\. Models can only be equal to other BaseModel instances\. For two model instances to be equal, they must have the same: Type \(or, in the case of generic models, non\-parametrized generic origin type\) Field values Extra values \(only relevant when model\_config\[&\#x27;extra&\#x27;\] == &\#x27;allow&\#x27; \) Private attribute values; models with different values of private attributes are no longer equal\. Models are no longer equal to the dicts containing their data\. Non\-generic models of different types are never equal\. Generic models with different origin types are never equal\. We don’t require exact type equality so that, for example, instances of MyGenericModel\[Any\] could be equal to instances of MyGenericModel\[int\] \. We have replaced the use of the \_\_root\_\_ field to specify a “custom root model” with a new type called RootModel which is intended to replace the functionality of using a field called \_\_root\_\_ in Pydantic V1\. Note, RootModel types no longer support the arbitrary\_types\_allowed config setting\. See this issue comment for an explanation\. We have significantly expanded Pydantic’s capabilities related to customizing serialization\. In particular, we have added the @field\_serializer , @model\_serializer , and @computed\_field decorators, which each address various shortcomings from Pydantic V1\. See Custom serializers for the usage docs of these new decorators\. Due to performance overhead and implementation complexity, we have now deprecated support for specifying json\_encoders in the model config\. This functionality was originally added for the purpose of achieving custom serialization logic, and we think the new serialization decorators are a better choice in most common scenarios\. We have changed the behavior related to serializing subclasses of models when they occur as nested fields in a parent model\. In V1, w
- Migration Guide \| Pydantic Docs — https://pydantic\.dev/docs/validation/latest/get\-started/migration
  Some of the built\-in data\-loading functionality has been slated for removal\. In particular, \`parse\_raw\` and \`parse\_file\` are now deprecated\. In Pydantic V2, \`model\_validate\_json\` works like \`parse\_raw\`\. Otherwise, you should load the data and then pass it to \`model\_validate\`\. The \`from\_orm\` method has been deprecated; you can now just use \`model\_validate\` \(equivalent to \`parse\_obj\` from Pydantic V1\) to achieve something similar, as long as you’ve set \`from\_attributes=True\` in the model config\. The \`\_\_eq\_\_\` method has changed for models\. \+ Models can only be equal to other \`BaseModel\` instances\. \+ For two model instances to be equal, they must have the same: \- Type \(or, in the case of generic models, non\-parametrized generic origin type\) \- Field values \[\.\.\.\] \#\#\#\# Changes to \`@validator\`’s allowed signatures In Pydantic V1, functions wrapped by \`@validator\` could receive keyword arguments with metadata about what was being validated\. Some of these arguments have been removed from \`@field\_validator\` in Pydantic V2: \`config\`: Pydantic V2’s config is now a dictionary instead of a class, which means this argument is no longer backwards compatible\. If you need to access the configuration you should migrate to \`@field\_validator\` and use \`info\.config\`\. \`field\`: this argument used to be a \`ModelField\` object, which was a quasi\-internal class that no longer exists in Pydantic V2\. Most of this information can still be accessed by using the field name from \`info\.field\_name\` to index into

## Usage and coverage

All recorded model requests have response usage; this is not invoice verification.

| Field | Recorded value |
| --- | --- |
| Model usage version | 1 |
| Attempted model requests | 8 |
| Responses with usage | 8 |
| Reported input tokens | 36148 |
| Reported output tokens | 10989 |

Sandbox SDK counters are versioned and internally settled.

| Adapter call | Attempted | Completed | Failed | Cancelled |
| --- | --- | --- | --- | --- |
| sdk\_calls | 16 | 16 | 0 | 0 |
| image\_use | 1 | 1 | 0 | 0 |
| run | 9 | 9 | 0 | 0 |
| read | 6 | 6 | 0 | 0 |

SDK invocations are not internal HTTP requests or billed Sandbox operations.
A returned nonzero process exit still completes an SDK call; failed/cancelled calls have an uncertain remote outcome.

Monetary/credit cost is not established by this export. No absent cost, unmatched model rate, or unreported service charge is replaced with zero.

## Recorded event history

### Event 1: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:37:39\.830238\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Run queued |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;queued&quot;\}

### Event 2: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:37:39\.942164\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Cloning and testing the repository inside Token Factory Sandbox |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;preparing&quot;\}

### Event 3: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:05\.631943\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Baseline pinned at 63cf7fdb4c62; 13/13 tests passed |

Recorded payload (escaped data):

\{&quot;commit\_sha&quot;: &quot;63cf7fdb4c62e119facb87fe108e9c278960a5c1&quot;\}

### Event 4: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:05\.632432\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Retrieving official guidance and requesting grounded Nemotron strategies |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;planning&quot;\}

### Event 5: research\.ready

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:10\.674616\+00:00 |
| Branch | Unknown (not recorded) |
| Message | 4 allowlisted official sources retained |

Recorded payload (escaped data):

\{&quot;citations&quot;: \[\{&quot;evidence&quot;: &quot;@validator and @root\_validator are deprecated @validator has been deprecated, and should be replaced with @field\_validator , which provides various new features and improvements\. The new @field\_validator decorator does not have the each\_item keyword argument; validators you want to apply to items within a generic container should be added by annotating the type argument\. See validators in Annotated metadata for details\. This looks like list\[Annotated\[int, Field\(ge=0\)\]\] Even if you keep using the deprecated @validator decorator, you can no longer add the field or config arguments to the signature of validator functions\. If you need access to these, you\\u2019ll need to migrate to @field\_validator \\u2014 see the next section for more details\. If you use the always=True keyword argument to a validator function, note that standard validators for the annotated type will also be applied even to defaults, not just the custom validators\. For example, despite the fact that the validator below will never error, the following code raises a ValidationError : from pydantic import BaseModel, validator class Model\(BaseModel\): x: str = 1 @validator\(&\#x27;x&\#x27;, always=True\) @classmethod def validate\_x\(cls, v\): return v Model\(\) @root\_validator has been deprecated, and should be replaced with @model\_validator , which also provides new features and improvements\. Be aware that the allowed signatures have changed \(see the relevant documentation \)\. Under some circumstances \(such as assignment when model\_config\[&\#x27;validate\_assignment&\#x27;\] is True \), the @model\_validator decorator will receive an instance of the model, not a dict of values\. You may need to be careful to handle this case\. Even if you keep using the deprecated @root\_validator decorator, due to refactors in validation logic, you can no longer run with skip\_on\_failure=False \(which is the default value of this keyword argument, so must be set explicitly to True \)\.&quot;, &quot;title&quot;: &quot;@validator and @root\_validator are deprecated&quot;, &quot;url&quot;: &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#validator\-and\-root\_validator\-are\-deprecated&quot;\}, \{&quot;evidence&quot;: &quot;Changes to config In Pydantic V2, to specify config on a model, you should set a class attribute called model\_config to be a dict with the key/value pairs you want to be used as the config\. The Pydantic V1 behavior to create a class called Config in the namespace of the parent BaseModel subclass is now deprecated\. When subclassing a model, the model\_config attribute is inherited\. This is helpful in the case where you\\u2019d like to use a base class with a given configuration for many models\. Note, if you inherit from multiple BaseModel subclasses, like class MyModel\(Model1, Model2\) , the non\-default settings in the model\_config attribute from the two models will be merged, and for any settings defined in both, those from Model2 will override those from Model1 \. The following config settings have been removed: allow\_mutation \\u2014 this has been removed\. You should be able to use frozen equivalently \(inverse of current use\)\. error\_msg\_templates fields \\u2014 this was the source of various bugs, so has been removed\. You should be able to use Annotated on fields to modify them as desired\. getter\_dict \\u2014 orm\_mode has been removed, and this implementation detail is no longer necessary\. smart\_union \- the default union\_mode in Pydantic V2 is &\#x27;smart&\#x27; \. underscore\_attrs\_are\_private \\u2014 the Pydantic V2 behavior is now the same as if this was always set to True in Pydantic V1\. json\_loads json\_dumps copy\_on\_model\_validation post\_init\_call The following config settings have been renamed: allow\_population\_by\_field\_name \\u2192 populate\_by\_name \(or validate\_by\_name starting in v2\.11\) anystr\_lower \\u2192 str\_to\_lower anystr\_strip\_whitespace \\u2192 str\_strip\_whitespace anystr\_upper \\u2192 str\_to\_upper keep\_untouched \\u2192 ignored\_types max\_anystr\_length \\u2192 str\_max\_length min\_anystr\_length \\u2192 str\_min\_length orm\_mode \\u2192 from\_attributes schema\_extra \\u2192 json\_schema\_extra validate\_all \\u2192 validate\_default See the ConfigDict API reference for more details\.&quot;, &quot;title&quot;: &quot;Changes to config&quot;, &quot;url&quot;: &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-config&quot;\}, \{&quot;evidence&quot;: &quot;Changes to pydantic\.BaseModel Various method names have been changed; all non\-deprecated BaseModel methods now have names matching either the format model\_\.\* or \_\_\.\*pydantic\.\*\_\_ \. Where possible, we have retained the deprecated methods with their old names to help ease migration, but calling them will emit DeprecationWarning s\. Pydantic V1 Pydantic V2 \_\_fields\_\_ model\_fields \_\_private\_attributes\_\_ \_\_pydantic\_private\_\_ \_\_validators\_\_ \_\_pydantic\_validator\_\_ construct\(\) model\_construct\(\) copy\(\) model\_copy\(\) dict\(\) model\_dump\(\) json\_schema\(\) model\_json\_schema\(\) json\(\) model\_dump\_json\(\) parse\_obj\(\) model\_validate\(\) update\_forward\_refs\(\) model\_rebuild\(\) Some of the built\-in data\-loading functionality has been slated for removal\. In particular, parse\_raw and parse\_file are now deprecated\. In Pydantic V2, model\_validate\_json works like parse\_raw \. Otherwise, you should load the data and then pass it to model\_validate \. The from\_orm method has been deprecated; you can now just use model\_validate \(equivalent to parse\_obj from Pydantic V1\) to achieve something similar, as long as you\\u2019ve set from\_attributes=True in the model config\. The \_\_eq\_\_ method has changed for models\. Models can only be equal to other BaseModel instances\. For two model instances to be equal, they must have the same: Type \(or, in the case of generic models, non\-parametrized generic origin type\) Field values Extra values \(only relevant when model\_config\[&\#x27;extra&\#x27;\] == &\#x27;allow&\#x27; \) Private attribute values; models with different values of private attributes are no longer equal\. Models are no longer equal to the dicts containing their data\. Non\-generic models of different types are never equal\. Generic models with different origin types are never equal\. We don\\u2019t require exact type equality so that, for example, instances of MyGenericModel\[Any\] could be equal to instances of MyGenericModel\[int\] \. We have replaced the use of the \_\_root\_\_ field to specify a \\u201ccustom root model\\u201d with a new type called RootModel which is intended to replace the functionality of using a field called \_\_root\_\_ in Pydantic V1\. Note, RootModel types no longer support the arbitrary\_types\_allowed config setting\. See this issue comment for an explanation\. We have significantly expanded Pydantic\\u2019s capabilities related to customizing serialization\. In particular, we have added the @field\_serializer , @model\_serializer , and @computed\_field decorators, which each address various shortcomings from Pydantic V1\. See Custom serializers for the usage docs of these new decorators\. Due to performance overhead and implementation complexity, we have now deprecated support for specifying json\_encoders in the model config\. This functionality was originally added for the purpose of achieving custom serialization logic, and we think the new serialization decorators are a better choice in most common scenarios\. We have changed the behavior related to serializing subclasses of models when they occur as nested fields in a parent model\. In V1, w&quot;, &quot;title&quot;: &quot;Changes to pydantic\.BaseModel&quot;, &quot;url&quot;: &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-pydanticbasemodel&quot;\}, \{&quot;evidence&quot;: &quot;Some of the built\-in data\-loading functionality has been slated for removal\. In particular, \`parse\_raw\` and \`parse\_file\` are now deprecated\. In Pydantic V2, \`model\_validate\_json\` works like \`parse\_raw\`\. Otherwise, you should load the data and then pass it to \`model\_validate\`\. The \`from\_orm\` method has been deprecated; you can now just use \`model\_validate\` \(equivalent to \`parse\_obj\` from Pydantic V1\) to achieve something similar, as long as you\\u2019ve set \`from\_attributes=True\` in the model config\. The \`\_\_eq\_\_\` method has changed for models\. \+ Models can only be equal to other \`BaseModel\` instances\. \+ For two model instances to be equal, they must have the same: \- Type \(or, in the case of generic models, non\-parametrized generic origin type\) \- Field values \[\.\.\.\] \#\#\#\# Changes to \`@validator\`\\u2019s allowed signatures In Pydantic V1, functions wrapped by \`@validator\` could receive keyword arguments with metadata about what was being validated\. Some of these arguments have been removed from \`@field\_validator\` in Pydantic V2: \`config\`: Pydantic V2\\u2019s config is now a dictionary instead of a class, which means this argument is no longer backwards compatible\. If you need to access the configuration you should migrate to \`@field\_validator\` and use \`info\.config\`\. \`field\`: this argument used to be a \`ModelField\` object, which was a quasi\-internal class that no longer exists in Pydantic V2\. Most of this information can still be accessed by using the field name from \`info\.field\_name\` to index into&quot;, &quot;title&quot;: &quot;Migration Guide \| Pydantic Docs&quot;, &quot;url&quot;: &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration&quot;\}\]\}

### Event 6: strategies\.ready

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.477289\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Nemotron produced 3 grounded, schema\-valid strategies |

Recorded payload (escaped data):

\{&quot;strategies&quot;: \[\{&quot;id&quot;: &quot;minimal&quot;, &quot;ordered\_steps&quot;: \[&quot;Update pyproject\.toml pydantic dependency to &gt;=2,&lt;3&quot;, &quot;Replace @validator with @field\_validator in models\.py&quot;, &quot;Replace @root\_validator with @model\_validator in models\.py&quot;, &quot;Replace Config class with model\_config dict using renamed settings&quot;, &quot;Update api\.py: parse\_obj\\u2192model\_validate, dict\\u2192model\_dump, parse\_raw\\u2192model\_validate\_json&quot;\], &quot;rationale&quot;: &quot;Smallest complete migration updating only deprecated APIs and config to v2 equivalents while preserving all public behavior and test compatibility\.&quot;, &quot;source\_urls&quot;: \[&quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#validator\-and\-root\_validator\-are\-deprecated&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-config&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-pydanticbasemodel&quot;\], &quot;target\_files&quot;: \[&quot;pyproject\.toml&quot;, &quot;src/sample\_app/models\.py&quot;, &quot;src/sample\_app/api\.py&quot;\], &quot;title&quot;: &quot;Minimal v1\\u2192v2 migration&quot;\}, \{&quot;id&quot;: &quot;compatibility&quot;, &quot;ordered\_steps&quot;: \[&quot;Update pyproject\.toml pydantic dependency to &gt;=2,&lt;3&quot;, &quot;Migrate validators to @field\_validator/@model\_validator with v2 signatures&quot;, &quot;Replace Config with model\_config using v2 setting names&quot;, &quot;Add deprecated method aliases \(parse\_obj, dict, parse\_raw\) wrapping v2 methods in models\.py&quot;, &quot;Preserve ValidationError import path from pydantic for test compatibility&quot;\], &quot;rationale&quot;: &quot;Maintains v1 method aliases and ValidationError compatibility at callers while migrating internals to v2, ensuring zero caller\-side changes\.&quot;, &quot;source\_urls&quot;: \[&quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#validator\-and\-root\_validator\-are\-deprecated&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-config&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-pydanticbasemodel&quot;\], &quot;target\_files&quot;: \[&quot;pyproject\.toml&quot;, &quot;src/sample\_app/models\.py&quot;\], &quot;title&quot;: &quot;Compatibility\-layer migration&quot;\}, \{&quot;id&quot;: &quot;refactor&quot;, &quot;ordered\_steps&quot;: \[&quot;Update pyproject\.toml pydantic dependency to &gt;=2,&lt;3&quot;, &quot;Replace Field\(alias=\.\.\.\) with Annotated\[\.\.\., Field\(validation\_alias=\.\.\.\)\]&quot;, &quot;Migrate @validator to @field\_validator with ValidationInfo parameter&quot;, &quot;Migrate @root\_validator to @model\_validator with mode=&\#x27;after&\#x27;&quot;, &quot;Replace Config class with model\_config dict using v2 settings&quot;, &quot;Add @field\_serializer for by\_alias serialization&quot;, &quot;Update api\.py to use model\_validate, model\_dump, model\_validate\_json&quot;, &quot;Remove deprecated method calls entirely&quot;\], &quot;rationale&quot;: &quot;Complete rewrite using native v2 patterns: Annotated fields, field\_serializer, model\_validator with info, and modern config\.&quot;, &quot;source\_urls&quot;: \[&quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#validator\-and\-root\_validator\-are\-deprecated&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-config&quot;, &quot;https://pydantic\.dev/docs/validation/latest/get\-started/migration/\#changes\-to\-pydanticbasemodel&quot;\], &quot;target\_files&quot;: \[&quot;pyproject\.toml&quot;, &quot;src/sample\_app/models\.py&quot;, &quot;src/sample\_app/api\.py&quot;\], &quot;title&quot;: &quot;Full refactor to v2 idioms&quot;\}\]\}

### Event 7: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.478235\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Three migration branches started from the pinned baseline |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;branching&quot;\}

### Event 8: branch\.started

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.479203\+00:00 |
| Branch | minimal |
| Message | Minimal v1→v2 migration: bounded patch loop started |

### Event 9: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.485989\+00:00 |
| Branch | minimal |
| Message | Minimal v1→v2 migration: proposal attempt 1/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 1, &quot;max\_attempts&quot;: 3\}

### Event 10: branch\.started

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.509485\+00:00 |
| Branch | compatibility |
| Message | Compatibility\-layer migration: bounded patch loop started |

### Event 11: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.515135\+00:00 |
| Branch | compatibility |
| Message | Compatibility\-layer migration: proposal attempt 1/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 1, &quot;max\_attempts&quot;: 3\}

### Event 12: branch\.started

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.529501\+00:00 |
| Branch | refactor |
| Message | Full refactor to v2 idioms: bounded patch loop started |

### Event 13: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:25\.531826\+00:00 |
| Branch | refactor |
| Message | Full refactor to v2 idioms: proposal attempt 1/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 1, &quot;max\_attempts&quot;: 3\}

### Event 14: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:40\.613482\+00:00 |
| Branch | compatibility |
| Message | Compatibility\-layer migration: proposal attempt 2/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 2, &quot;max\_attempts&quot;: 3\}

### Event 15: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:40\.659027\+00:00 |
| Branch | refactor |
| Message | Full refactor to v2 idioms: proposal attempt 2/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 2, &quot;max\_attempts&quot;: 3\}

### Event 16: branch\.completed

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:41\.543761\+00:00 |
| Branch | minimal |
| Message | 13/13 tests passed |

Recorded payload (escaped data):

\{&quot;result&quot;: \{&quot;changed\_files&quot;: 3, &quot;changed\_lines&quot;: 44, &quot;checkpoint\_id&quot;: &quot;38a6d383\-4ae3\-41bb\-81a7\-8a56202f0f1f&quot;, &quot;diagnostics&quot;: &quot;\.\.\.\.\.\.\.\.\.\.\.\.\.                                                            \[100%\]\\n13 passed, 25 warnings in 0\.10s\\nUP045 \[\*\] Use \`X \| None\` for type annotations\\n  \-\-&gt; src/sample\_app/models\.py:11:15\\n   \|\\n 9 \|     name: str\\n10 \|     email: str\\n11 \|     nickname: Optional\[str\] = None\\n   \|               ^^^^^^^^^^^^^\\n12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\)\\n   \|\\nhelp: Convert to \`X \| None\`\\n   \|\\n10 \|     email: str\\n   \-     nickname: Optional\[str\] = None\\n11 \+     nickname: str \| None = None\\n12 \|     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\)\\n   \|\\n\\nFound 1 error\.\\n\[\*\] 1 fixable with the \`\-\-fix\` option\.&quot;, &quot;elapsed\_seconds&quot;: 7\.882017541996902, &quot;failure\_reason&quot;: null, &quot;lint\_findings&quot;: 1, &quot;patch&quot;: &quot;diff \-\-git a/pyproject\.toml b/pyproject\.toml\\n\-\-\- a/pyproject\.toml\\n\+\+\+ b/pyproject\.toml\\n@@ \-6,7 \+6,7 @@\\n name = \\&quot;branchshift\-pydantic\-v1\-fixture\\&quot;\\n version = \\&quot;0\.1\.0\\&quot;\\n requires\-python = \\&quot;&gt;=3\.10\\&quot;\\n\-dependencies = \[\\&quot;pydantic&gt;=1\.10,&lt;2\\&quot;\]\\n\+dependencies = \[\\&quot;pydantic&gt;=2,&lt;3\\&quot;\]\\n \\n \[project\.optional\-dependencies\]\\n test = \[\\&quot;pytest&gt;=8\\&quot;\]\\ndiff \-\-git a/src/sample\_app/models\.py b/src/sample\_app/models\.py\\n\-\-\- a/src/sample\_app/models\.py\\n\+\+\+ b/src/sample\_app/models\.py\\n@@ \-1,36 \+1,44 @@\\n from datetime import datetime\\n from typing import Optional\\n \\n\-from pydantic import BaseModel, Field, root\_validator, validator\\n\+from pydantic import BaseModel, Field, field\_validator, model\_validator\\n \\n \\n class User\(BaseModel\):\\n\-    user\_id: int = Field\(alias=\\&quot;id\\&quot;\)\\n\+    user\_id: int = Field\(alias=&\#x27;id&\#x27;\)\\n     name: str\\n     email: str\\n     nickname: Optional\[str\] = None\\n     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\)\\n \\n\-    @validator\(\\&quot;name\\&quot;\)\\n\+    @field\_validator\(&\#x27;name&\#x27;\)\\n     def name\_must\_not\_be\_blank\(cls, value: str\) \-&gt; str:\\n         if not value\.strip\(\):\\n\-            raise ValueError\(\\&quot;name must not be blank\\&quot;\)\\n\+            raise ValueError\(&\#x27;name must not be blank&\#x27;\)\\n         return value\.strip\(\)\\n \\n\-    @validator\(\\&quot;email\\&quot;\)\\n\+    @field\_validator\(&\#x27;email&\#x27;\)\\n     def normalize\_email\(cls, value: str\) \-&gt; str:\\n         return value\.strip\(\)\.lower\(\)\\n \\n\-    @root\_validator\(skip\_on\_failure=True\)\\n\+    @model\_validator\(mode=&\#x27;after&\#x27;\)\\n     def nickname\_differs\_from\_name\(cls, values\):\\n\-        if values\.get\(\\&quot;nickname\\&quot;\) == values\.get\(\\&quot;name\\&quot;\):\\n\-            raise ValueError\(\\&quot;nickname must differ from name\\&quot;\)\\n\+        \# Handle both dict \(validation\) and model instance \(assignment validation\)\\n\+        if isinstance\(values, dict\):\\n\+            nickname = values\.get\(&\#x27;nickname&\#x27;\)\\n\+            name = values\.get\(&\#x27;name&\#x27;\)\\n\+        else:\\n\+            nickname = getattr\(values, &\#x27;nickname&\#x27;, None\)\\n\+            name = getattr\(values, &\#x27;name&\#x27;, None\)\\n\+        if nickname == name:\\n\+            raise ValueError\(&\#x27;nickname must differ from name&\#x27;\)\\n         return values\\n \\n\-    class Config:\\n\-        allow\_population\_by\_field\_name = True\\n\-        anystr\_strip\_whitespace = True\\n\-        orm\_mode = True\\n\+    model\_config = \{\\n\+        &\#x27;populate\_by\_name&\#x27;: True,\\n\+        &\#x27;str\_strip\_whitespace&\#x27;: True,\\n\+        &\#x27;from\_attributes&\#x27;: True,\\n\+    \}\\n \\n \\n class Project\(BaseModel\):\\n@@ \-38,8 \+46,8 @@\\n     owner: User\\n     archived: bool = False\\n \\n\-    @validator\(\\&quot;slug\\&quot;\)\\n\+    @field\_validator\(&\#x27;slug&\#x27;\)\\n     def slug\_is\_lowercase\(cls, value: str\) \-&gt; str:\\n         if value \!= value\.lower\(\):\\n\-            raise ValueError\(\\&quot;slug must be lowercase\\&quot;\)\\n\+            raise ValueError\(&\#x27;slug must be lowercase&\#x27;\)\\n         return value\\ndiff \-\-git a/src/sample\_app/api\.py b/src/sample\_app/api\.py\\n\-\-\- a/src/sample\_app/api\.py\\n\+\+\+ b/src/sample\_app/api\.py\\n@@ \-2,13 \+2,13 @@\\n \\n \\n def parse\_user\(payload: dict\) \-&gt; User:\\n\-    return User\.parse\_obj\(payload\)\\n\+    return User\.model\_validate\(payload\)\\n \\n \\n def serialize\_user\(user: User\) \-&gt; dict:\\n\-    return user\.dict\(by\_alias=True, exclude\_none=True\)\\n\+    return user\.model\_dump\(by\_alias=True, exclude\_none=True\)\\n \\n \\n def parse\_project\_json\(payload: str\) \-&gt; Project:\\n\-    return Project\.parse\_raw\(payload\)\\n\+    return Project\.model\_validate\_json\(payload\)\\n \\n&quot;, &quot;patch\_applicable&quot;: true, &quot;pip\_check\_passed&quot;: true, &quot;pip\_exit\_code&quot;: 0, &quot;pydantic\_major&quot;: 2, &quot;status&quot;: &quot;passed&quot;, &quot;strategy\_id&quot;: &quot;minimal&quot;, &quot;test\_contract\_preserved&quot;: true, &quot;test\_exit\_code&quot;: 0, &quot;tests\_collected&quot;: 13, &quot;tests\_failed&quot;: 0, &quot;tests\_passed&quot;: 13\}\}

### Event 17: branch\.completed

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:54\.657964\+00:00 |
| Branch | compatibility |
| Message | 13/13 tests passed |

Recorded payload (escaped data):

\{&quot;result&quot;: \{&quot;changed\_files&quot;: 2, &quot;changed\_lines&quot;: 71, &quot;checkpoint\_id&quot;: &quot;6292762c\-373d\-4fbe\-ad9f\-fc557dc5f356&quot;, &quot;diagnostics&quot;: &quot;\.\.\.\.\.\.\.\.\.\.\.\.\.                                                            \[100%\]\\n13 passed, 14 warnings in 0\.10s\\nF401 \[\*\] \`typing\.Optional\` imported but unused\\n \-\-&gt; src/sample\_app/models\.py:2:20\\n  \|\\n1 \| from datetime import datetime\\n2 \| from typing import Optional\\n  \|                    ^^^^^^^^\\n3 \|\\n4 \| from pydantic import BaseModel, Field, field\_validator, model\_validator\\n  \|\\nhelp: Remove unused import: \`typing\.Optional\`\\n  \|\\n1 \| from datetime import datetime\\n  \- from typing import Optional\\n2 \|\\n  \|\\n\\nFound 1 error\.\\n\[\*\] 1 fixable with the \`\-\-fix\` option\.&quot;, &quot;elapsed\_seconds&quot;: 15\.693857833000948, &quot;failure\_reason&quot;: null, &quot;lint\_findings&quot;: 1, &quot;patch&quot;: &quot;diff \-\-git a/pyproject\.toml b/pyproject\.toml\\n\-\-\- a/pyproject\.toml\\n\+\+\+ b/pyproject\.toml\\n@@ \-6,7 \+6,7 @@\\n name = \\&quot;branchshift\-pydantic\-v1\-fixture\\&quot;\\n version = \\&quot;0\.1\.0\\&quot;\\n requires\-python = \\&quot;&gt;=3\.10\\&quot;\\n\-dependencies = \[\\&quot;pydantic&gt;=1\.10,&lt;2\\&quot;\]\\n\+dependencies = \[\\&quot;pydantic&gt;=2,&lt;3\\&quot;\]\\n \\n \[project\.optional\-dependencies\]\\n test = \[\\&quot;pytest&gt;=8\\&quot;\]\\ndiff \-\-git a/src/sample\_app/models\.py b/src/sample\_app/models\.py\\n\-\-\- a/src/sample\_app/models\.py\\n\+\+\+ b/src/sample\_app/models\.py\\n@@ \-1,36 \+1,57 @@\\n from datetime import datetime\\n from typing import Optional\\n \\n\-from pydantic import BaseModel, Field, root\_validator, validator\\n\+from pydantic import BaseModel, Field, field\_validator, model\_validator\\n \\n \\n class User\(BaseModel\):\\n\-    user\_id: int = Field\(alias=\\&quot;id\\&quot;\)\\n\+    user\_id: int = Field\(alias=&\#x27;id&\#x27;\)\\n     name: str\\n     email: str\\n\-    nickname: Optional\[str\] = None\\n\+    nickname: str \| None = None\\n     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\)\\n \\n\-    @validator\(\\&quot;name\\&quot;\)\\n\+    @field\_validator\(&\#x27;name&\#x27;\)\\n\+    @classmethod\\n     def name\_must\_not\_be\_blank\(cls, value: str\) \-&gt; str:\\n         if not value\.strip\(\):\\n\-            raise ValueError\(\\&quot;name must not be blank\\&quot;\)\\n\+            raise ValueError\(&\#x27;name must not be blank&\#x27;\)\\n         return value\.strip\(\)\\n \\n\-    @validator\(\\&quot;email\\&quot;\)\\n\+    @field\_validator\(&\#x27;email&\#x27;\)\\n\+    @classmethod\\n     def normalize\_email\(cls, value: str\) \-&gt; str:\\n         return value\.strip\(\)\.lower\(\)\\n \\n\-    @root\_validator\(skip\_on\_failure=True\)\\n\+    @model\_validator\(mode=&\#x27;after&\#x27;\)\\n\+    @classmethod\\n     def nickname\_differs\_from\_name\(cls, values\):\\n\-        if values\.get\(\\&quot;nickname\\&quot;\) == values\.get\(\\&quot;name\\&quot;\):\\n\-            raise ValueError\(\\&quot;nickname must differ from name\\&quot;\)\\n\+        if isinstance\(values, dict\):\\n\+            nickname = values\.get\(&\#x27;nickname&\#x27;\)\\n\+            name = values\.get\(&\#x27;name&\#x27;\)\\n\+        else:\\n\+            nickname = getattr\(values, &\#x27;nickname&\#x27;, None\)\\n\+            name = getattr\(values, &\#x27;name&\#x27;, None\)\\n\+        if nickname == name:\\n\+            raise ValueError\(&\#x27;nickname must differ from name&\#x27;\)\\n         return values\\n \\n\-    class Config:\\n\-        allow\_population\_by\_field\_name = True\\n\-        anystr\_strip\_whitespace = True\\n\-        orm\_mode = True\\n\+    model\_config = \{\\n\+        &\#x27;populate\_by\_name&\#x27;: True,\\n\+        &\#x27;str\_strip\_whitespace&\#x27;: True,\\n\+        &\#x27;from\_attributes&\#x27;: True,\\n\+    \}\\n\+\\n\+    @classmethod\\n\+    def parse\_obj\(cls, obj\):\\n\+        return cls\.model\_validate\(obj\)\\n\+\\n\+    def dict\(self, \*, by\_alias=False, exclude\_none=False, \*\*kwargs\):\\n\+        return self\.model\_dump\(by\_alias=by\_alias, exclude\_none=exclude\_none, \*\*kwargs\)\\n\+\\n\+    @classmethod\\n\+    def parse\_raw\(cls, data\):\\n\+        return cls\.model\_validate\_json\(data\)\\n \\n \\n class Project\(BaseModel\):\\n@@ \-38,8 \+59,26 @@\\n     owner: User\\n     archived: bool = False\\n \\n\-    @validator\(\\&quot;slug\\&quot;\)\\n\+    @field\_validator\(&\#x27;slug&\#x27;\)\\n\+    @classmethod\\n     def slug\_is\_lowercase\(cls, value: str\) \-&gt; str:\\n         if value \!= value\.lower\(\):\\n\-            raise ValueError\(\\&quot;slug must be lowercase\\&quot;\)\\n\+            raise ValueError\(&\#x27;slug must be lowercase&\#x27;\)\\n         return value\\n\+\\n\+    model\_config = \{\\n\+        &\#x27;populate\_by\_name&\#x27;: True,\\n\+        &\#x27;str\_strip\_whitespace&\#x27;: True,\\n\+        &\#x27;from\_attributes&\#x27;: True,\\n\+    \}\\n\+\\n\+    @classmethod\\n\+    def parse\_obj\(cls, obj\):\\n\+        return cls\.model\_validate\(obj\)\\n\+\\n\+    def dict\(self, \*, by\_alias=False, exclude\_none=False, \*\*kwargs\):\\n\+        return self\.model\_dump\(by\_alias=by\_alias, exclude\_none=exclude\_none, \*\*kwargs\)\\n\+\\n\+    @classmethod\\n\+    def parse\_raw\(cls, data\):\\n\+        return cls\.model\_validate\_json\(data\)\\n&quot;, &quot;patch\_applicable&quot;: true, &quot;pip\_check\_passed&quot;: true, &quot;pip\_exit\_code&quot;: 0, &quot;pydantic\_major&quot;: 2, &quot;status&quot;: &quot;passed&quot;, &quot;strategy\_id&quot;: &quot;compatibility&quot;, &quot;test\_contract\_preserved&quot;: true, &quot;test\_exit\_code&quot;: 0, &quot;tests\_collected&quot;: 13, &quot;tests\_failed&quot;: 0, &quot;tests\_passed&quot;: 13\}\}

### Event 18: branch\.progress

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:38:54\.684774\+00:00 |
| Branch | refactor |
| Message | Full refactor to v2 idioms: proposal attempt 3/3 started |

Recorded payload (escaped data):

\{&quot;attempt&quot;: 3, &quot;max\_attempts&quot;: 3\}

### Event 19: branch\.completed

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:39:06\.807618\+00:00 |
| Branch | refactor |
| Message | Branch failed safely: Test execution failed; inspect the test diagnostic |

Recorded payload (escaped data):

\{&quot;result&quot;: \{&quot;changed\_files&quot;: 3, &quot;changed\_lines&quot;: 58, &quot;checkpoint\_id&quot;: &quot;dcef0c62\-9ba9\-40e6\-b9e7\-70a9aaa215c4&quot;, &quot;diagnostics&quot;: &quot;Validation failed\. Repair only the declared files\. tests=11/13, pip\_check=True, lint\_findings=1, pydantic\_major=2, reason=Test execution failed; inspect the test diagnostic\.\\nTest failure \\u2014 tests\.test\_api::test\_dict\_boundary: AssertionError: assert \{&\#x27;user\_id&\#x27;: 3\.\.\.39, 5, 96088\)\} == \{&\#x27;id&\#x27;: 3, &\#x27;na\.\.\.39, 5, 96088\)\}\\n  \\n  Omitting 3 identical items, use \-vv to show\\n  Left contains 1 more item:\\n  \{&\#x27;user\_id&\#x27;: 3\}\\n  Right contains 1 more item:\\n  \{&\#x27;id&\#x27;: 3\}\\n  Use \-v to get more diff\\nTest failure \\u2014 tests\.test\_models::test\_alias\_is\_used\_during\_serialization: KeyError: &\#x27;id&\#x27;\\n\.F\.\.\.\.\.\.\.\.F\.\.                                                            \[100%\]\\n=================================== FAILURES ===================================\\n\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ test\_dict\_boundary \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\\ntests/test\_api\.py:10: in test\_dict\_boundary\\n    assert payload == \{\\&quot;id\\&quot;: 3, \\&quot;name\\&quot;: \\&quot;Lin\\&quot;, \\&quot;email\\&quot;: \\&quot;l@e\.com\\&quot;, \\&quot;created\_at\\&quot;: payload\[\\&quot;created\_at\\&quot;\]\}\\nE   AssertionError: assert \{&\#x27;user\_id&\#x27;: 3\.\.\.39, 5, 96088\)\} == \{&\#x27;id&\#x27;: 3, &\#x27;na\.\.\.39, 5, 96088\)\}\\nE     \\nE     Omitting 3 identical items, use \-vv to show\\nE     Left contains 1 more item:\\nE     \{&\#x27;user\_id&\#x27;: 3\}\\nE     Right contains 1 more item:\\nE     \{&\#x27;id&\#x27;: 3\}\\nE     Use \-v to get more diff\\n\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ test\_alias\_is\_used\_during\_serialization \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\\ntests/test\_models\.py:45: in test\_alias\_is\_used\_during\_serialization\\n    assert payload\[\\&quot;id\\&quot;\] == 7 and \\&quot;user\_id\\&quot; not in payload\\n           ^^^^^^^^^^^^^\\nE   KeyError: &\#x27;id&\#x27;\\n=========================== short test summary info ============================\\nFAILED tests/test\_api\.py::test\_dict\_boundary \- AssertionError: assert \{&\#x27;user\_\.\.\.\\nFAILED tests/test\_models\.py::test\_alias\_is\_used\_during\_serialization \- KeyErr\.\.\.\\n2 failed, 11 passed, 25 warnings in 0\.11s\\nF401 \[\*\] \`typing\.Optional\` imported but unused\\n \-\-&gt; src/sample\_app/models\.py:2:20\\n  \|\\n1 \| from datetime import datetime\\n2 \| from typing import Optional\\n  \|                    ^^^^^^^^\\n3 \|\\n4 \| from pydantic import BaseModel, Field, ValidationInfo, field\_validator, model\_validator\\n  \|\\nhelp: Remove unused import: \`typing\.Optional\`\\n  \|\\n1 \| from datetime import datetime\\n  \- from typing import Optional\\n2 \|\\n  \|\\n\\nFound 1 error\.\\n\[\*\] 1 fixable with the \`\-\-fix\` option\.&quot;, &quot;elapsed\_seconds&quot;: 23\.227317791999667, &quot;failure\_reason&quot;: &quot;Test execution failed; inspect the test diagnostic&quot;, &quot;lint\_findings&quot;: 1, &quot;patch&quot;: &quot;diff \-\-git a/pyproject\.toml b/pyproject\.toml\\n\-\-\- a/pyproject\.toml\\n\+\+\+ b/pyproject\.toml\\n@@ \-6,7 \+6,7 @@\\n name = \\&quot;branchshift\-pydantic\-v1\-fixture\\&quot;\\n version = \\&quot;0\.1\.0\\&quot;\\n requires\-python = \\&quot;&gt;=3\.10\\&quot;\\n\-dependencies = \[\\&quot;pydantic&gt;=1\.10,&lt;2\\&quot;\]\\n\+dependencies = \[\\&quot;pydantic&gt;=2,&lt;3\\&quot;\]\\n \\n \[project\.optional\-dependencies\]\\n test = \[\\&quot;pytest&gt;=8\\&quot;\]\\ndiff \-\-git a/src/sample\_app/models\.py b/src/sample\_app/models\.py\\n\-\-\- a/src/sample\_app/models\.py\\n\+\+\+ b/src/sample\_app/models\.py\\n@@ \-1,36 \+1,47 @@\\n from datetime import datetime\\n from typing import Optional\\n \\n\-from pydantic import BaseModel, Field, root\_validator, validator\\n\+from pydantic import BaseModel, Field, ValidationInfo, field\_validator, model\_validator\\n \\n \\n class User\(BaseModel\):\\n\-    user\_id: int = Field\(alias=\\&quot;id\\&quot;\)\\n\+    user\_id: int = Field\(validation\_alias=&\#x27;id&\#x27;\)\\n     name: str\\n     email: str\\n\-    nickname: Optional\[str\] = None\\n\+    nickname: str \| None = None\\n     created\_at: datetime = Field\(default\_factory=datetime\.utcnow\)\\n \\n\-    @validator\(\\&quot;name\\&quot;\)\\n\-    def name\_must\_not\_be\_blank\(cls, value: str\) \-&gt; str:\\n\+    @field\_validator\(&\#x27;name&\#x27;\)\\n\+    @classmethod\\n\+    def name\_must\_not\_be\_blank\(cls, value: str, info: ValidationInfo\) \-&gt; str:\\n         if not value\.strip\(\):\\n\-            raise ValueError\(\\&quot;name must not be blank\\&quot;\)\\n\+            raise ValueError\(&\#x27;name must not be blank&\#x27;\)\\n         return value\.strip\(\)\\n \\n\-    @validator\(\\&quot;email\\&quot;\)\\n\-    def normalize\_email\(cls, value: str\) \-&gt; str:\\n\+    @field\_validator\(&\#x27;email&\#x27;\)\\n\+    @classmethod\\n\+    def normalize\_email\(cls, value: str, info: ValidationInfo\) \-&gt; str:\\n         return value\.strip\(\)\.lower\(\)\\n \\n\-    @root\_validator\(skip\_on\_failure=True\)\\n\-    def nickname\_differs\_from\_name\(cls, values\):\\n\-        if values\.get\(\\&quot;nickname\\&quot;\) == values\.get\(\\&quot;name\\&quot;\):\\n\-            raise ValueError\(\\&quot;nickname must differ from name\\&quot;\)\\n\+    @model\_validator\(mode=&\#x27;after&\#x27;\)\\n\+    @classmethod\\n\+    def nickname\_differs\_from\_name\(cls, values, info: ValidationInfo\):\\n\+        \# Handle both dict \(during validation\) and model instance \(during assignment\)\\n\+        if isinstance\(values, dict\):\\n\+            nickname = values\.get\(&\#x27;nickname&\#x27;\)\\n\+            name = values\.get\(&\#x27;name&\#x27;\)\\n\+        else:\\n\+            nickname = getattr\(values, &\#x27;nickname&\#x27;, None\)\\n\+            name = getattr\(values, &\#x27;name&\#x27;, None\)\\n\+        if nickname == name:\\n\+            raise ValueError\(&\#x27;nickname must differ from name&\#x27;\)\\n         return values\\n \\n\-    class Config:\\n\-        allow\_population\_by\_field\_name = True\\n\-        anystr\_strip\_whitespace = True\\n\-        orm\_mode = True\\n\+    model\_config = \{\\n\+        &\#x27;populate\_by\_name&\#x27;: True,\\n\+        &\#x27;str\_strip\_whitespace&\#x27;: True,\\n\+        &\#x27;from\_attributes&\#x27;: True,\\n\+    \}\\n \\n \\n class Project\(BaseModel\):\\n@@ \-38,8 \+49,9 @@\\n     owner: User\\n     archived: bool = False\\n \\n\-    @validator\(\\&quot;slug\\&quot;\)\\n\-    def slug\_is\_lowercase\(cls, value: str\) \-&gt; str:\\n\+    @field\_validator\(&\#x27;slug&\#x27;\)\\n\+    @classmethod\\n\+    def slug\_is\_lowercase\(cls, value: str, info: ValidationInfo\) \-&gt; str:\\n         if value \!= value\.lower\(\):\\n\-            raise ValueError\(\\&quot;slug must be lowercase\\&quot;\)\\n\+            raise ValueError\(&\#x27;slug must be lowercase&\#x27;\)\\n         return value\\ndiff \-\-git a/src/sample\_app/api\.py b/src/sample\_app/api\.py\\n\-\-\- a/src/sample\_app/api\.py\\n\+\+\+ b/src/sample\_app/api\.py\\n@@ \-2,13 \+2,13 @@\\n \\n \\n def parse\_user\(payload: dict\) \-&gt; User:\\n\-    return User\.parse\_obj\(payload\)\\n\+    return User\.model\_validate\(payload\)\\n \\n \\n def serialize\_user\(user: User\) \-&gt; dict:\\n\-    return user\.dict\(by\_alias=True, exclude\_none=True\)\\n\+    return user\.model\_dump\(by\_alias=True, exclude\_none=True\)\\n \\n \\n def parse\_project\_json\(payload: str\) \-&gt; Project:\\n\-    return Project\.parse\_raw\(payload\)\\n\+    return Project\.model\_validate\_json\(payload\)\\n \\n&quot;, &quot;patch\_applicable&quot;: true, &quot;pip\_check\_passed&quot;: true, &quot;pip\_exit\_code&quot;: 0, &quot;pydantic\_major&quot;: 2, &quot;status&quot;: &quot;failed&quot;, &quot;strategy\_id&quot;: &quot;refactor&quot;, &quot;test\_contract\_preserved&quot;: true, &quot;test\_exit\_code&quot;: 1, &quot;tests\_collected&quot;: 13, &quot;tests\_failed&quot;: 2, &quot;tests\_passed&quot;: 11\}\}

### Event 20: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:39:06\.811822\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Ranking branch evidence and revalidating the candidate on a clean baseline |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;evaluating&quot;\}

### Event 21: winner\.selected

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:39:13\.048129\+00:00 |
| Branch | minimal |
| Message | Minimal won the deterministic evidence gate |

Recorded payload (escaped data):

\{&quot;winner\_id&quot;: &quot;minimal&quot;\}

### Event 22: run\.status

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:39:13\.048965\+00:00 |
| Branch | Unknown (not recorded) |
| Message | Verified live migration package ready |

Recorded payload (escaped data):

\{&quot;status&quot;: &quot;completed&quot;\}

### Event 23: run\.completed

| Field | Recorded value |
| --- | --- |
| Time | 2026\-09\-10T06:39:13\.049099\+00:00 |
| Branch | minimal |
| Message | Winner patch and live evidence report are ready |
