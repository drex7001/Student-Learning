Act as a senior AI researcher, causal-inference specialist, educational psychologist, and data scientist with expertise in Bayesian Networks, early-warning systems, inclusive education, and the Sri Lankan school context.

I am developing a research prototype for identifying students who may require early support to prevent school disengagement and dropout in Sri Lankan schools.

The system must not be presented as a diagnostic, disciplinary, or automated decision-making system. It should estimate uncertainty, identify potentially modifiable barriers, and support human review by teachers, counsellors, social-service officers, special-education professionals, and families.

The model must avoid treating protected or sensitive characteristics—such as disability, neurotype, gender, ethnicity, language, or geographic sector—as inherently causing dropout. Model environmental barriers, lack of support, exclusion, and unmet needs as causal mechanisms wherever appropriate.

Use Python and the current `pgmpy` API, particularly:

- `pgmpy.models.DiscreteBayesianNetwork`
- `pgmpy.factors.discrete.TabularCPD`
- `pgmpy.sampling.BayesianModelSampling`
- `pgmpy.inference.VariableElimination`

## Part 1: Critically review the proposed causal model

Before writing code:

1. Explain the difference between:
   - a causal factor,
   - a predictive indicator,
   - a mediator,
   - a confounder,
   - a proxy variable,
   - and an outcome.

2. Review every proposed edge and classify it as:
   - supported by Sri Lankan evidence,
   - supported mainly by international evidence,
   - expert hypothesis requiring validation,
   - or potentially inappropriate.

3. Do not claim that the graph is causally valid merely because it is a DAG.

4. Provide an “edge justification table” containing:
   - Parent node
   - Child node
   - Proposed mechanism
   - Evidence level
   - Potential confounders
   - Whether the factor is modifiable
   - Ethical or fairness concerns

5. Prefer Sri Lankan Ministry of Education, Department of Census and Statistics, UNICEF Sri Lanka, UNESCO, World Bank, ILO, peer-reviewed Sri Lankan studies, and validated international systematic reviews.

## Part 2: Construct a temporally valid DAG

Create a static two-period Bayesian Network representing risk over consecutive school terms.

Use previous-term and current-term variables where necessary to prevent unrealistic feedback cycles. For example:

`Previous_Attendance -> Current_Academic_Performance -> Current_Academic_Stress -> Current_Attendance -> Next_Term_Dropout_Risk`

Do not create both `Attendance -> Academic_Performance` and `Academic_Performance -> Attendance` within the same time period.

### Recommended nodes

#### Background and contextual variables

1. `Sector`
   - Urban
   - Rural
   - Estate

2. `Grade_Band`
   - Primary
   - Junior_Secondary
   - OLevel_ALevel

3. `Economic_Strain`
   - Low
   - Moderate
   - High

4. `Parent_Education`
   - Low
   - Secondary
   - Post_Secondary

5. `Parent_Availability`
   - Available
   - Limited_or_Away

6. `Neuro_Type`
   - Typical
   - ADHD
   - ASD

`Neuro_Type` must never have a direct edge to `Dropout_Risk`. It may influence the kind of educational support a student needs, but risk should arise through environmental mismatch, exclusion, distress, or insufficient accommodation.

#### Household and access variables

7. `Child_Labour_Household_Duties`
   - Low
   - High

8. `Transport_Burden`
   - Low
   - High

9. `Food_Health_Burden`
   - Low
   - High

10. `Home_Educational_Support`
    - Adequate
    - Limited

#### School environment variables

11. `WASH_Quality`
    - Adequate
    - Inadequate

12. `Sensory_Environment`
    - Supportive
    - Overloading

13. `School_Accommodation`
    - Adequate
    - Inadequate

14. `Bullying_Social_Exclusion`
    - Low
    - High

15. `Teacher_Resource_Adequacy`
    - Adequate
    - Limited

#### Mediating variables

16. `Support_Mismatch`
    - Low
    - High

17. `School_Distress`
    - Low
    - High

18. `Access_Barrier`
    - Low
    - High

19. `Previous_Attendance`
    - Regular
    - Irregular

20. `Current_Academic_Performance`
    - Adequate
    - Low

21. `Current_Academic_Stress`
    - Low
    - High

22. `Psychological_Attendance_Barrier`
    - Low
    - High

23. `Current_Attendance`
    - Regular
    - Irregular

24. `School_Engagement`
    - High
    - Low

25. `Next_Term_Dropout_Risk`
    - Low
    - Medium
    - High

### Required causal edges

Use the following as expert hypotheses to be reviewed rather than unquestioned truths:

#### Socio-economic mechanisms

- `Sector -> Transport_Burden`
- `Sector -> Teacher_Resource_Adequacy`
- `Sector -> WASH_Quality`
- `Economic_Strain -> Child_Labour_Household_Duties`
- `Economic_Strain -> Food_Health_Burden`
- `Economic_Strain -> Transport_Burden`
- `Parent_Education -> Home_Educational_Support`
- `Parent_Availability -> Home_Educational_Support`
- `Parent_Availability -> Child_Labour_Household_Duties`

#### Neurodivergence and inclusion mechanisms

- `Neuro_Type -> Support_Mismatch`
- `School_Accommodation -> Support_Mismatch`
- `Support_Mismatch -> School_Distress`
- `Sensory_Environment -> School_Distress`
- `Bullying_Social_Exclusion -> School_Distress`

These edges must capture an interaction-like mechanism: an ASD or ADHD student should not automatically have high distress. Distress should be substantially lower when accommodations and the sensory environment are supportive.

#### WASH and health mechanisms

- `WASH_Quality -> Food_Health_Burden`
- `WASH_Quality -> School_Distress`

Explain that inadequate WASH may affect attendance through illness, avoidance, dignity, privacy, menstrual-hygiene barriers, or sensory discomfort. Do not assume that every student experiences the same mechanism.

#### Access and attendance mechanisms

- `Transport_Burden -> Access_Barrier`
- `Child_Labour_Household_Duties -> Access_Barrier`
- `Food_Health_Burden -> Access_Barrier`

- `School_Distress -> Psychological_Attendance_Barrier`
- `Current_Academic_Stress -> Psychological_Attendance_Barrier`

- `Previous_Attendance -> Current_Attendance`
- `Access_Barrier -> Current_Attendance`
- `Psychological_Attendance_Barrier -> Current_Attendance`

#### Academic and engagement mechanisms

- `Previous_Attendance -> Current_Academic_Performance`
- `Teacher_Resource_Adequacy -> Current_Academic_Performance`
- `Home_Educational_Support -> Current_Academic_Performance`

- `Current_Academic_Performance -> Current_Academic_Stress`
- `Grade_Band -> Current_Academic_Stress`

- `Current_Academic_Performance -> School_Engagement`
- `Home_Educational_Support -> School_Engagement`
- `Bullying_Social_Exclusion -> School_Engagement`

#### Outcome mechanisms

- `Current_Attendance -> Next_Term_Dropout_Risk`
- `School_Engagement -> Next_Term_Dropout_Risk`
- `Grade_Band -> Next_Term_Dropout_Risk`

Do not create direct edges from every background variable to `Next_Term_Dropout_Risk`. Preserve interpretable causal pathways through mediators unless evidence strongly supports a direct effect.

Keep each node’s parent count manageable. Prefer intermediate mechanism nodes rather than CPDs with an unreasonably large number of parent combinations.

## Part 3: Define transparent CPDs

Create valid `TabularCPD` objects for every node.

Requirements:

1. Clearly label all initial values as:
   “Illustrative expert-elicited priors for software testing; not validated Sri Lankan prevalence estimates.”

2. Do not describe invented probabilities as empirically established.

3. Use explicit `state_names` for every CPD.

4. Ensure every conditional column sums to 1.0.

5. Encode monotonic and psychologically plausible behaviour. Examples:
   - Higher economic strain should generally increase child-labour and health burdens.
   - Adequate accommodations should reduce support mismatch for ADHD and ASD students.
   - A supportive sensory environment should reduce school distress.
   - High bullying should increase distress and reduce engagement.
   - High access and psychological barriers should increase irregular attendance.
   - Irregular attendance combined with low engagement should produce the highest dropout-risk distribution.

6. Avoid deterministic probabilities of exactly 0 or 1 except where logically necessary.

7. For binary variables with several parents, create reusable helper functions that construct a `TabularCPD` from transparent additive-risk or logistic parameters instead of hard-coding unreadable matrices.

8. Include unit tests that verify:
   - every CPD column sums to 1,
   - all probabilities are between 0 and 1,
   - the model is acyclic,
   - every model node has a CPD,
   - and `model.check_model()` returns `True`.

## Part 4: Production-quality Python implementation

Write one complete runnable Python module.

Organize it into functions such as:

- `build_structure()`
- `build_cpds()`
- `validate_cpds()`
- `build_model()`
- `generate_synthetic_data()`
- `infer_dropout_risk()`
- `compare_scenarios()`
- `run_sensitivity_analysis()`
- `main()`

Additional requirements:

- Use type hints.
- Use `logging`, not scattered `print()` calls.
- Use a fixed random seed.
- Add meaningful docstrings.
- Raise clear exceptions for invalid evidence or unknown states.
- Store node state definitions in one central dictionary.
- Avoid global mutable state.
- Make the inference function suitable for later use inside FastAPI.
- Return serializable dictionaries from inference functions.
- Export 10,000 synthetic records to CSV.
- Include a synthetic `student_id`.
- Mark the generated dataset clearly as synthetic.
- Do not include real student-identifying information.
- Print or log the DAG edges and model-validation result.

## Part 5: Inference scenarios

Use `VariableElimination` to calculate observational posterior probabilities.

Implement at least these comparisons:

### Scenario A: Environmental mismatch

1. ASD student, inadequate WASH, overloading sensory environment, and inadequate accommodation.
2. ASD student, inadequate WASH, overloading sensory environment, but adequate accommodation.
3. Typical student with the same inadequate WASH and school conditions.

Explain why Scenario 2 is the ethically important comparison: it estimates how modifiable school support may alter predicted risk rather than suggesting that ASD itself should be changed.

### Scenario B: Socio-economic access barriers

Compare:

1. High economic strain, high child-labour or household duties, and high transport burden.
2. High economic strain with low household duties and low transport burden.

### Scenario C: Protective factors

Compare an irregularly attending student under:

1. Limited home support, high bullying, and low school engagement.
2. Adequate home support, low bullying, and high school engagement.

Return:

- posterior probability for each `Next_Term_Dropout_Risk` state,
- the highest-risk state,
- evidence used,
- and differences between scenarios.

## Part 6: Observational versus causal interpretation

Explicitly explain that:

`P(Dropout_Risk | School_Accommodation = Adequate)`

is an observational conditional probability and is not automatically equal to:

`P(Dropout_Risk | do(School_Accommodation = Adequate))`.

Where supported by the installed pgmpy version, include a separate intervention function using a mutilated graph or the model’s intervention functionality.

Never perform an intervention on immutable characteristics such as `Neuro_Type`. Demonstrate interventions only on modifiable factors, such as:

- improving school accommodations,
- improving WASH quality,
- reducing bullying,
- reducing transport burden,
- providing educational support,
- or reducing child-labour demands.

## Part 7: Sensitivity and calibration

Because the CPDs initially come from expert assumptions:

1. Run sensitivity analysis on at least:
   - the effect of accommodation on support mismatch,
   - WASH quality on health burden,
   - child labour on access barriers,
   - irregular attendance on dropout risk.

2. Vary selected probabilities by ±10% and report whether scenario rankings change.

3. Explain how future CPDs should be calibrated using:
   - longitudinal attendance records,
   - grade progression,
   - transfer and school-leaving records,
   - school WASH audits,
   - transport information,
   - household surveys,
   - counsellor assessments,
   - and ethically collected student-support information.

4. Recommend Bayesian parameter estimation with informative priors once suitable Sri Lankan data becomes available.

5. Explain that synthetic records generated from manually assigned CPDs cannot validate the model because they merely reproduce its assumptions.

## Part 8: Fairness, safety, and governance

Add a final section covering:

- human review,
- informed consent and legal authority,
- data minimisation,
- role-based access,
- audit logs,
- encryption,
- retention limits,
- handling of disability and mental-health information,
- false-positive and false-negative harms,
- subgroup calibration,
- avoiding punitive intervention,
- and a student or guardian appeal process.

Do not recommend using this model to deny education, discipline students, rank schools, label children permanently, or report families to authorities automatically.

The final response must contain:

1. Causal-model critique
2. Edge-justification table
3. Final DAG
4. Complete executable Python code
5. CPD rationale
6. Synthetic-data generation
7. Inference examples
8. Observational-versus-interventional explanation
9. Sensitivity analysis
10. Validation and deployment recommendations
11. Ethical and fairness limitations
12. Research sources