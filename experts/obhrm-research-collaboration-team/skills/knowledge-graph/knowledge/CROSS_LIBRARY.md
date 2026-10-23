# 三库交叉索引（OBHRM 研究资料库）

> 关联均来自源文档文本真实匹配，未编造。已补全 `construct_id`，并以构念(construct_id)为稳定键构建索引。

## 一、库概览

| 库 | 节点数 | 校验通过 | 待核验 | 索引文件 |
|---|---|---|---|---|
| 量表库 | 599 | 599 | 0 | `../../scale-library/knowledge/_scale_index.json` |
| 理论库 | 134 | 134 | 0 | `../../theory-library/knowledge/_theory_index.json` |
| R分析库 | 108 | — | — | `../../r-analysis/knowledge/_r_index.json` |

> 注：R 分析库 108 节点与 r-analysis `_r_index.json` 108 个脚本一致（含 3 个非构念域脚本亦入跨库索引）。

## 二、关联规模

- **量表 → 理论**：62 条（58 个量表在其背景中引用了理论，其中 4 个量表关联 2 条、其余各 1 条 `via` 媒介词）
- **理论 → 量表**：7 条（6 个理论文本中提及了量表变量，其中 1 个理论关联 2 条）
- **R 方法适用量表库**：54 个；**适用理论库**：80 个（见 `_meta.counts.r_applicable_scale / r_applicable_theory`）
- **construct_index 构念聚合条目**：134 个


## 三、稳定键 construct_index（按构念聚合跨库节点）

| construct_id | 构念(中/英) | 理论 | 量表 | R方法 |
|---|---|---|---|---|
| actor_network_theory | 行动者网络理论/Actor Network Theory | T110 | — | — |
| affect_as_information_theory | 情感信息理论/Affect-as-Information Theory | T034 | — | — |
| affective_events_theory | 情感事件理论/Affective Events Theory | T033 | S582 | — |
| affordance_theory | 可供性理论/Affordance Theory | T019 | — | — |
| algorithmic_imaginary | 算法想象/Algorithmic Imaginary | T065 | — | — |
| attribution_theory | 归因理论/Attribution theory | T029 | S306, S512, S582, S598 | — |
| boundary_theory | 边界理论/Boundary Theory | T086 | S038 | — |
| bounded_rationality | 有限理性/Bounded Rationality | T095 | — | — |
| carnivalesque_theory | 狂欢理论/Carnivalesque Theory | T121 | — | — |
| charismatic_leadership | 魅力型领导理论/Charismatic Leadership | T094 | — | — |
| cognition_affect_conation_perspective | 认知-情感-意动框架/Cognition-Affect-Conation Perspective | T079 | — | — |
| cognitive_development_theory | 认知发展理论/Cognitive Development Theory | T124 | — | — |
| cognitive_load_theory | 认知负荷理论/Cognitive Load Theory | T080 | — | — |
| collective_memory_theory | 集体记忆理论/Collective Memory Theory | T089 | — | — |
| com_b | 能力、机会、动机和行为模型/COM-B | T069 | — | — |
| complex_adaptive_systems | 复杂适应系统/Complex Adaptive Systems | T023 | — | — |
| comprehensive_model_of_information_seeking | 信息寻求综合模型/Comprehensive Model of Information Seeking | T011 | — | — |
| computers_are_social_actors_casa | 计算机为社会行动者/Computers are Social Actors, CASA | T078 | — | — |
| consequences_norms_inaction_model | CNI模型/Consequences-Norms-Inaction Model | T001 | — | — |
| conservation_of_resources_theory | 资源保存理论/Conservation of Resources Theory | T083 | S038 | — |
| construal_level_theory | 解释水平理论/Construal Level Theory | T076 | — | — |
| coordinated_management_of_meaning | 意义协调管理理论/Coordinated Management of Meaning | T107 | — | — |
| cultivation_analysis | 涵化理论/cultivation analysis | T051 | — | — |
| cultural_capital_theory | 文化资本理论/Cultural Capital Theory | T045 | — | — |
| cultural_dimensions_theory | 文化维度理论/Cultural Dimensions Theory | T043 | — | — |
| cultural_discount | 文化折扣理论/Cultural Discount | T042 | — | — |
| cultural_identity | 文化认同/Cultural Identity | T044 | — | — |
| cyborg | 赛博格/Cyborg | T084 | — | — |
| dramaturgical_theory | 拟剧理论/Dramaturgical Theory | T040 | — | — |
| dual_process_theory | 双过程理论/Dual Process Theory | T016 | — | — |
| elaborated_intrusion_theory | 欲望侵入理论/Elaborated Intrusion Theory | T049 | — | — |
| elaboration_likelihood_model | 详尽可能性模型/Elaboration Likelihood Model | T081 | — | — |
| embodied_cognition_theory | 具身认知理论/Embodied Cognition Theory | T098 | — | — |
| emotional_contagion_theory | 情绪传染理论/Emotional Contagion Theory | T100 | — | — |
| equity_theory | 公平理论/Equity Theory | T133 | — | — |
| erg_theory | ERG理论/ERG Theory | T131 | — | — |
| expectancy_theory | 期望理论/Expectancy Theory | T132 | — | — |
| expectancy_violations_theory | 期望违背理论/Expectancy Violations Theory | T102 | — | — |
| expectation_confirmation_theory_ect | 期望确认理论/Expectation-Confirmation Theory, ECT | T047 | — | — |
| face_negotiation_theory | 面子协商理论/Face-Negotiation Theory | T090 | — | — |
| family_systems_theory | 家庭系统理论/Family Systems Theory | T028 | — | — |
| fiedler_contingency_model | 费德勒权变领导理论/Fiedler Contingency Model | T082 | — | — |
| field_theory | 场域理论/Field Theory | T021 | — | — |
| flow | 心流理论/Flow | T030 | — | — |
| framing_theory | 框架理论/Framing Theory | T048 | — | — |
| fundamental_interpersonal_relations_orientation | 人际关系三维理论/Fundamental interpersonal relations orientation | T096 | — | — |
| gamification | 游戏化理论/Gamification | T106 | — | — |
| gaze_theory | 凝视理论/Gaze Theory | T013 | — | — |
| goal_setting_theory | 目标设定理论/Goal-Setting Theory | T055 | — | — |
| hierarchy_of_needs | 需要层次理论/Hierarchy of Needs | T128 | — | — |
| high_and_low_context_theory | 高低语境理论/High and Low Context Theory | T093 | — | — |
| imprinting_theory | 烙印理论/Imprinting Theory | T052 | — | — |
| information_cascade | 信息流瀑/Information Cascade | T012 | — | — |
| information_foraging_theory | 信息觅食理论/Information Foraging Theory | T114 | — | — |
| information_processing_theory | 信息加工理论/Information Processing Theory | T010 | S184, S293, S355, S476 | — |
| innovation_diffusion_theory | 创新扩散理论/Innovation Diffusion Theory | T115 | S045, S266, S310, S367, S591 | — |
| innovation_resistance_theory | 创新抵抗理论/Innovation Resistance Theory | T014 | — | — |
| interaction_ritual_chain_theory | 互动仪式链理论/Interaction Ritual Chain Theory | T007 | — | — |
| jd_r模型 | 工作需求-资源/JD-R模型 | T003 | S329 | — |
| leader_member_exchange_lmx | 领导-成员交换理论/Leader-Member Exchange, LMX | T091 | — | — |
| media_multiplexity_theory | 媒介多重性理论/Media Multiplexity Theory | T025 | — | — |
| media_richness_theory_mrt | 媒介丰富性理论/Media Richness Theory, MRT | T024 | — | — |
| mediatized_society | 媒介化社会/Mediatized Society | T099 | — | — |
| medium_theory | 媒介情景理论/Medium Theory | T026 | — | — |
| mental_accounting_theory | 心理账户理论/Mental Accounting Theory | T031 | — | — |
| moral_licensing_theory | 道德许可理论/Moral Licensing Theory | T125 | — | — |
| narrative_transportation_theory | 叙述传输理论/Narrative Transportation Theory | T018 | — | — |
| objectification_theory | 客体化理论/Objectification Theory | T027 | — | — |
| organization_change_theory | 组织变革理论/Organization Change Theory | T067 | — | — |
| organizational_information_processing_theory_oipt | 组织信息加工理论/Organizational Information Processing Theory, OIPT | T066 | — | — |
| para_social_interaction_theory | ：准社会交往理论/Para-social Interaction Theory | T112 | — | — |
| path_goal_theory | 路径-目标领导理论/Path-Goal Theory | T085 | — | — |
| perceived_value_theory | 感知价值理论/Perceived Value Theory | T101 | — | — |
| perma_theory_of_well_being | PERMA幸福理论/PERMA Theory of Well-Being | T004 | — | — |
| person_affect_cognition_execution | I-PACE理论模型/Person-Affect-Cognition-Execution | T002 | — | — |
| person_environment_fit_theory_p_e_fit | 个人-环境匹配理论/Person-Environment Fit Theory，P-E Fit | T006 | — | — |
| platform_capitalism | 平台资本主义/Platform Capitalism | T118 | — | — |
| policy_network_theory | 政策网络理论/Policy Network Theory | T041 | — | — |
| privacy_calculus_theory | 隐私计算理论/Privacy Calculus Theory | T088 | — | — |
| privacy_paradox | 隐私悖论/Privacy Paradox | T087 | — | — |
| psychological_resilience | 心理韧性/Psychological Resilience | T119 | — | — |
| regulatory_focus_theory | 调节定向理论/Regulatory Focus Theory | T105 | — | — |
| reinforcement_theory | 强化理论/Reinforcement Theory | T134 | — | — |
| relative_deprivation_theory | 相对剥夺理论/Relative Deprivation Theory | T056 | — | — |
| risk_information_seeking_and_processing_model_risp | 风险信息寻求与加工模型/Risk Information Seeking and Processing Model , RISP | T092 | — | — |
| role_stress | 角色压力/Role Stress | T075 | S410 | — |
| scene_theory | 场景理论/Scene Theory | T022 | — | — |
| schema_theory | 图式理论/Schema Theory | T020 | — | — |
| seci_model_of_knowledge_dimensions | 知识创造与转换的SECI模型/SECI Model of Knowledge Dimensions | T057 | — | — |
| self_categorization_theory | 自我分类理论/Self-Categorization Theory | T071 | — | — |
| self_determination_theory | 自我决定理论/Self-determination theory | T070 | S168, S330, S393, S466, S522, S596 | — |
| self_directed_learning | 自我导向学习/Self-Directed Learning | T073 | — | — |
| self_presentation_theory | 自我呈现理论/Self-Presentation Theory | T072 | S543 | — |
| self_regulation_theory | 自我调节理论/Self-Regulation Theory | T074 | — | — |
| sensemaking_theory | 意义构建理论/Sensemaking Theory | T036 | — | — |
| sensory_marketing | 感官营销/Sensory Marketing | T037 | — | — |
| situated_learning_theory | 情境学习理论/Situated Learning Theory | T032 | — | — |
| social_baseline_theory | 社会基线理论/Social Baseline Theory | T122 | — | — |
| social_capital_theory | 社会资本理论/Social Capital Theory | T064 | — | — |
| social_cognition_theory | 社会认知理论/Social Cognition Theory | T127 | S320, S389, S485, S563 | — |
| social_comparison_theory | 社会比较理论/Social Comparison Theory | T123 | — | — |
| social_exchange_theory | 社会交换理论/Social Exchange Theory | T126 | S001, S059, S076, S188, S363, S540 | — |
| social_facilitation_theory | 社会促进理论/Social Facilitation Theory | T059 | — | — |
| social_identity_theory | 社会认同理论/Social Identity Theory | T063 | S001, S351, S418 | — |
| social_learning_theory | 社会学习理论/Social Learning Theory | T060 | S176 | — |
| social_network_theory | 社会网络理论/Social Network Theory | T109 | — | — |
| social_penetration_theory | 社会渗透理论/Social Penetration Theory | T061 | — | — |
| social_presence_theory | 社会临场感理论/Social Presence Theory | T058 | — | — |
| social_role_theory | 社会角色理论/Social Role Theory | T062 | — | — |
| social_support_theory | 社会支持理论/Social Support Theory | T104 | S293 | — |
| socio_technical_systems_theory_sts | 社会技术系统理论/Socio-technical Systems Theory, STS | T103 | S018 | — |
| speech_act_theory | 言语行为理论/Speech Act Theory | T077 | — | — |
| stakeholder_theory | 利益相关者/Stakeholder Theory | T116 | S062, S138, S147, S247, S392, S394, S408, S447, S448, S536, S551, S552 | — |
| stereotype_content_model | 刻板印象内容模型/Stereotype Content Model | T015 | — | — |
| stimulus_organism_response | SOR理论/stimulus-organism-response | T005 | — | — |
| structuration_theory | 结构化理论/Structuration Theory | T068 | S012 | — |
| task_technology_fit_ttf | 任务技术适配理论/Task-Technology Fit, TTF | T097 | — | — |
| technology_acceptance_model | 技术接受模型/Technology Acceptance Model | T039 | S033 | — |
| technology_organization_environment_toe | 技术-组织-环境框架/Technology-Organization-Environment, TOE | T038 | — | — |
| textual_poachers | 文本盗猎者/Textual Poachers | T046 | — | — |
| the_circuit_of_culture | 文化循环理论/The Circuit of Culture | T120 | — | — |
| the_media_equation | 媒介等同理论/The Media Equation | T117 | — | — |
| theory_of_consumption_values | 消费价值理论/Theory of Consumption Values | T050 | — | — |
| theory_of_emotional_intelligence | 情绪智力理论/Theory of Emotional Intelligence | T035 | — | — |
| theory_of_needs | 成就需要理论/Theory of Needs | T130 | — | — |
| theory_of_planned_behavior_tpb | 计划行为理论/Theory of Planned Behavior, TPB | T111 | S265, S357, S523, S559 | — |
| theory_of_reasoned_action_tra | 理性行为理论/Theory of Reasoned Action, TRA | T054 | — | — |
| trait_activation_theory | 特质激活理论/Trait Activation Theory | T053 | — | — |
| transactional_leadership | 交易型领导理论/Transactional Leadership | T009 | — | — |
| transactive_memory_system | 交互记忆系统/Transactive Memory System | T008 | S594 | — |
| transformational_leadership | 变革型领导理论/Transformational Leadership | T017 | S446, S595 | — |
| trust_transfer_theory | 信任转移理论/Trust Transfer Theory | T113 | — | — |
| two_factor_theory | 双因素理论/Two-Factor Theory | T129 | — | — |
| utaut_utaut2 | 技术接受和使用统一模型/UTAUT、UTAUT2 | T108 | — | — |

## 四、量表 → 理论（背景引用，带 construct_id 溯源）

| 量表 | 变量 | 引用理论 | 构念键 | 命中词 |
|---|---|---|---|---|
| S001 | 3i-HRM量表 | 社会认同理论/Social Identity Theory | social_identity_theory | 社会认同理论 |
| S001 | 3i-HRM量表 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S012 | 适应性结构量表 | 结构化理论/Structuration Theory | structuration_theory | Structuration Theory |
| S018 | 算法能力量表 | 社会技术系统理论/Socio-technical Systems Theory, STS | socio_technical_systems_theory_sts | 社会技术系统理论 |
| S033 | 工作中人工智能态度量表 | 技术接受模型/Technology Acceptance Model | technology_acceptance_model | 技术接受模型 |
| S038 | 双方向工作-家庭冲突问卷） | 资源保存理论/Conservation of Resources Theory | conservation_of_resources_theory | 资源保存理论 |
| S038 | 双方向工作-家庭冲突问卷） | 边界理论/Boundary Theory | boundary_theory | 边界理论 |
| S045 | 购买中心参与性量表 | 创新扩散理论/Innovation Diffusion Theory | innovation_diffusion_theory | 创新扩散理论 |
| S059 | 基于认知的信任量表 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S062 | 认知合法性量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S076 | 权变奖励领导行为 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S138 | 创业能力 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S147 | 伦理型领导量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S168 | 经济激励动机量表 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S176 | 个人内在自我调节焦点问卷 | 社会学习理论/Social Learning Theory | social_learning_theory | 社会学习理论 |
| S184 | 绿色和谐人力资源管理实践量表 | 信息加工理论/Information Processing Theory | information_processing_theory | 信息加工理论 |
| S188 | 团队整合量表 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S247 | 主动提升人力资源系统量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S265 | 干预准备度工具 | 计划行为理论/Theory of Planned Behavior, TPB | theory_of_planned_behavior_tpb | Theory of Planned Behavior, TPB |
| S266 | 组织内扩散量表 | 创新扩散理论/Innovation Diffusion Theory | innovation_diffusion_theory | 创新扩散理论 |
| S293 | 领导恢复支持量表 | 信息加工理论/Information Processing Theory | information_processing_theory | 信息加工理论 |
| S293 | 领导恢复支持量表 | 社会支持理论/Social Support Theory | social_support_theory | 社会支持理论 |
| S306 | 管理者对寻求反馈行为的动机归因量表 | 归因理论/Attribution theory | attribution_theory | 归因理论 |
| S310 | 市场和技术动荡量表 | 创新扩散理论/Innovation Diffusion Theory | innovation_diffusion_theory | 创新扩散理论 |
| S320 | 道德推脱量表 | 社会认知理论/Social Cognition Theory | social_cognition_theory | 社会认知理论 |
| S329 | 多维感知工作能力量表 | 工作需求-资源/JD-R模型 | jd_r模型 | 工作需求-资源 |
| S330 | 多维工作狂热量表 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S351 | 组织认同量表 | 社会认同理论/Social Identity Theory | social_identity_theory | 社会认同理论 |
| S355 | 组织心理健康披露支持量表 | 信息加工理论/Information Processing Theory | information_processing_theory | 信息加工理论 |
| S357 | 大流行安全氛围量表 | 计划行为理论/Theory of Planned Behavior, TPB | theory_of_planned_behavior_tpb | 计划行为理论 |
| S363 | 组织支持的PCMT模型量表 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S367 | 感知贡献量表 | 创新扩散理论/Innovation Diffusion Theory | innovation_diffusion_theory | 创新扩散理论 |
| S389 | 政治效能感量表 | 社会认知理论/Social Cognition Theory | social_cognition_theory | 社会认知理论 |
| S392 | 实践智慧量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S393 | 出勤动机量表 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S394 | 亲社会违规行为量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S408 | 责任型领导问卷 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S410 | 角色压力源量表 | 角色压力/Role Stress | role_stress | 角色压力 |
| S418 | 企业微博情景下的社 | 社会认同理论/Social Identity Theory | social_identity_theory | 社会认同理论 |
| S446 | 变革型领导问卷 | 变革型领导理论/Transformational Leadership | transformational_leadership | 变革型领导理论 |
| S447 | 对与同事和直接领导的信任量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S448 | 对高层管理者的信任量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S466 | 工作需求满足量表 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S476 | 出勤压力量表 | 信息加工理论/Information Processing Theory | information_processing_theory | 信息加工理论 |
| S485 | 个体道德推脱量表 | 社会认知理论/Social Cognition Theory | social_cognition_theory | 社会认知理论 |
| S512 | 销售人员归因和行为意图量表 | 归因理论/Attribution theory | attribution_theory | 归因理论 |
| S522 | 自我决定量表 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S523 | 自我效能和行为意图量表 | 计划行为理论/Theory of Planned Behavior, TPB | theory_of_planned_behavior_tpb | 计划行为理论 |
| S536 | 服务型领导量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S540 | 社会和经济交换量表 | 社会交换理论/Social Exchange Theory | social_exchange_theory | 社会交换理论 |
| S543 | 社会赞许性量表 | 自我呈现理论/Self-Presentation Theory | self_presentation_theory | 自我呈现理论 |
| S551 | 利益相关者属性量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S552 | 利益相关者的整合量表 | 利益相关者/Stakeholder Theory | stakeholder_theory | 利益相关者 |
| S559 | 主观规范和感知行为控制量表 | 计划行为理论/Theory of Planned Behavior, TPB | theory_of_planned_behavior_tpb | 计划行为理论 |
| S563 | 主管恢复支持量表 | 社会认知理论/Social Cognition Theory | social_cognition_theory | 社会认知理论 |
| S582 | 组织内部沟通阴暗面量表 | 归因理论/Attribution theory | attribution_theory | 归因理论 |
| S582 | 组织内部沟通阴暗面量表 | 情感事件理论/Affective Events Theory | affective_events_theory | 情感事件理论 |
| S591 | 高层管理支持量表 | 创新扩散理论/Innovation Diffusion Theory | innovation_diffusion_theory | 创新扩散理论 |
| S594 | 交互记忆系统量表 | 交互记忆系统/Transactive Memory System | transactive_memory_system | 交互记忆系统 |
| S595 | 变革型领导量表 | 变革型领导理论/Transformational Leadership | transformational_leadership | Transformational Leadership |
| S596 | 治疗性自我调节问卷 | 自我决定理论/Self-determination theory | self_determination_theory | 自我决定理论 |
| S598 | 信任与不信任量表 | 归因理论/Attribution theory | attribution_theory | 归因理论 |

## 五、理论 → 量表（文本提及变量，带 construct_id 溯源）

| 理论 | 提及量表 | 构念键 | 命中词 |
|---|---|---|---|
| 工作需求-资源/JD-R模型 | S343 (组织公民行为) | jd_r模型 | 组织公民行为 |
| 工作需求-资源/JD-R模型 | S469 (工作家庭冲突) | jd_r模型 | 工作家庭冲突 |
| 交互记忆系统/Transactive Memory System | S594 (交互记忆系统量表) | transactive_memory_system | Transactive Memory Systems |
| 自我决定理论/Self-determination theory | S332 (需求满足量表) | self_determination_theory | 需求满足量表 |
| 领导-成员交换理论/Leader-Member Exchange, LMX | S343 (组织公民行为) | leader_member_exchange_lmx | 组织公民行为 |
| 社会技术系统理论/Socio-technical Systems Theory, STS | S053 (Hindrance Stressor and Appraisal Scale) | socio_technical_systems_theory_sts | Challenge |
| 社会比较理论/Social Comparison Theory | S474 (职场排斥) | social_comparison_theory | 职场排斥 |
## 六、R 方法 → 适用库（语义归类）

| 方法 | 标题 | 适用库 | 关联构念 |
|---|---|---|---|
| 1.1 | R语言简介 | general |  |
| 1.2.1 | 中英文界面切换 | general |  |
| 1.2.2 | R的升级 | general |  |
| 1.3.1 | 使用R包（安装与加载） | general |  |
| 1.3.2 | R包的安装目录 | general |  |
| 1.3.3 | 引用R语言或某个具体的包 | general |  |
| 1.3.4 | 从GitHub安装R包 | general |  |
| 1.3.5 | 查询R包的下载量 | general |  |
| 10.1.1 | 基础LPA（剖面识别） | general |  |
| 10.1.2 | LPA含协变量（主效应） | general |  |
| 10.1.3 | LPA含远端结果（剖面预测结果变量） | general |  |
| 10.1.4 | LPA含中介效应（剖面通过中介影响结果） | theory |  |
| 10.1.5 | LPA含调节效应（剖面与调节变量的交互） | theory |  |
| 10.2.1 | 基础LCA（类别识别） | general |  |
| 10.2.2 | LCA含协变量（主效应） | general |  |
| 10.2.3 | LCA含远端结果（类别预测结果变量） | general |  |
| 10.2.4 | LCA含中介效应（类别通过中介影响结果） | theory |  |
| 10.2.5 | LCA含调节效应（类别与调节变量的交互） | theory |  |
| 10.3.1 | 基础潜增长模型 | general |  |
| 10.3.2 | LGA含协变量（预测增长） | general |  |
| 10.3.3 | LGA含中介效应 | theory |  |
| 10.3.4 | LGA含调节效应 | theory |  |
| 10.3.5 | LGA有调节的中介 | theory |  |
| 10.3.6 | LGA有中介的调节 | theory |  |
| 10.3.7 | 增长混合模型（GMM，识别不同增长轨迹组） | general |  |
| 10.3.8 | 潜增长中介（Latent Growth Mediation，纵向机制的完整形式） | theory |  |
| 11.1 | 元分析 | theory |  |
| 11.2 | SEM元分析（MASEM：两阶段结构方程建模） | theory |  |
| 11.3 | 三层元分析 | theory |  |
| 12.1 | 多层验证性因素分析（MCFA） | scale, theory |  |
| 12.2 | 多层线性模型：零模型与方差分解 | theory |  |
| 12.3 | 随机截距模型与随机斜率模型 | general |  |
| 12.4 | 跨水平交互效应与中心化策略 | general |  |
| 12.5 | 多层中介效应模型 | theory |  |
| 12.5.1 | 跨层次有调节的中介（Cross-level Moderated Mediation） | scale, theory |  |
| 12.5.2 | 跨层次有中介的调节（Cross-level Mediated Moderation） | theory |  |
| 12.6 | 广义线性混合模型（GLMM） | general |  |
| 12.7.1 | ESM基础分析（零模型与个体内/间效应） | scale |  |
| 12.7.2 | ESM多层中介（1-1-1模型） | theory |  |
| 12.7.3 | ESM双中介（并行多重中介） | theory |  |
| 12.7.4 | ESM链式中介 | theory |  |
| 12.7.5 | ESM有调节的多层中介 | theory |  |
| 12.7.6 | 动态结构方程模型（DSEM，密集纵向的前沿方法） | general |  |
| 2.1 | 数据读取 | theory |  |
| 2.2.1 | 变量重命名 | general |  |
| 2.2.2 | 变量重编码（反向计分） | general |  |
| 2.2.3 | 数据类型转换 | general |  |
| 2.2.4 | 简单计算 | general |  |
| 2.3.1 | 异常值检测 | general |  |
| 2.3.2 | 重复值处理 | general |  |
| 2.3.3 | 变量标签管理 | general |  |
| 2.3.4 | 缺失数据处理 | general |  |
| 2.3.5 | 样本筛选与抽样 | general |  |
| 2.4 | 数据合并 | general |  |
| 2.5 | 数据中心化 | general |  |
| 2.6 | 数据保存 | general |  |
| 2.7 | 数据可视化 | general |  |
| 3.1 | 模糊集定性比较分析（fsQCA） | general |  |
| 3.2 | 必要条件分析（NCA） | general |  |
| 4.1 | 扎根理论分析（RQDA） | general |  |
| 4.2 | 文本预处理与语料库构建 | general |  |
| 4.3 | 主题模型（LDA） | general |  |
| 4.4 | 文本网络分析 | general |  |
| 4.5 | 文档自动分类 | general |  |
| 4.6 | 本地大语言模型分析（Ollama） | general |  |
| 5.1 | 样本量预估（横向研究） | general |  |
| 5.2 | 纵向研究的效力分析（Power Analysis for Longitudinal Studies） | scale, theory |  |
| 6.1 | 信度分析 | scale |  |
| 6.10 | 法则效度检验（Nomological Validity） | scale |  |
| 6.2 | 探索性因素分析（EFA） | scale |  |
| 6.2.1 | 主成分分析（PCA） | general |  |
| 6.3 | 探索性结构方程模型（ESEM） | scale |  |
| 6.4 | 一阶验证性因素分析（CFA） | scale |  |
| 6.5 | 二阶验证性因素分析 | scale |  |
| 6.6 | BiFactor验证性因素分析 | scale |  |
| 6.7 | 测量不变性（跨组与纵向 Measurement Invariance） | scale |  |
| 6.8 | 共同方法偏差检验（CMV） | theory |  |
| 6.9 | 判别效度检验（HTMT / Fornell-Larcker） | scale |  |
| 7.1 | 描述性统计 | general |  |
| 7.2 | 相关分析 | general |  |
| 7.3 | T检验 | general |  |
| 7.4 | 单因素方差分析（ANOVA） | general |  |
| 7.5 | 多因素方差分析（Factorial ANOVA） | scale |  |
| 7.6 | 多元方差分析（MANOVA） | general |  |
| 7.7 | 非参数检验 | scale |  |
| 7.8 | 协方差分析（ANCOVA） | theory |  |
| 7.9 | 重复测量方差分析 | scale |  |
| 8.1 | 多元线性回归 | theory |  |
| 8.2 | 多层回归分析（层次回归） | theory |  |
| 8.3 | 逻辑回归 | theory |  |
| 9.1 | 结构方程模型分析（SEM） | general |  |
| 9.2 | 中介效应分析 | theory |  |
| 9.2.1 | 并行多重中介 | theory |  |
| 9.2.2 | 链式/序列中介 | theory |  |
| 9.2.3 | 多重结果中介 | theory |  |
| 9.2.4 | 中介效应量与敏感性分析 | theory |  |
| 9.2.5 | 多自变量中介（Multiple X Mediation） | theory |  |
| 9.3 | 调节效应分析 | theory |  |
| 9.4 | 有调节的中介 | theory |  |
| 9.5 | 有中介的调节 | theory |  |
| 9.6 | 非线性SEM（潜变量交互与二次效应） | general |  |
| 9.7 | 交叉滞后模型（CLPM） | general |  |
| 9.8.1 | 基础响应面分析 | general |  |
| 9.8.2 | 响应面分析的调节效应 | theory |  |
| 9.8.3 | 响应面分析的中介效应 | theory |  |
