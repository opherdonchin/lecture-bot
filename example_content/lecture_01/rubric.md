# Mastery Rubric

## 1. Lecture metadata

- **Lecture title:** Lecture 1: Probabilities
- **Lecture identifier:** lecture_01_probabilities
- **Source files used:** `slides.md`, `handout.md`, `notebook.md`, `minutes.json`
- **Main purpose of the lecture:** Introduce statistics as a way of reasoning from finite, imperfect measurements toward claims about reality through models, then motivate probability, probability distributions, and distribution summaries as tools for representing uncertainty.
- **Did the instructional minutes materially deepen the interpretation of the lecture?** Yes. The minutes materially sharpened what should count as understanding in at least five places: the reality–data–model relation, processed and finite data, precision vs. validity vs. reliability, aleatory vs. epistemic uncertainty, and the interpretation of PDF/CDF, skewness, and kurtosis.

## 2. Lecture map

| Section / segment | Summary | Relative importance |
|---|---|---|
| 1.1–1.2 Why statistics exists / What is statistics | Statistics is motivated as indirect reasoning about hidden reality through measurements and models. The lecture makes the reality–data–model loop central rather than decorative. | core |
| 1.3 What is data | Data are finite recorded outputs of measurement processes, not reality itself. The lecture explicitly allows processed or derived quantities to count as data when they remain part of the measurement pipeline. | core |
| 1.4 Imperfect data | The lecture distinguishes major ways data can fail before analysis even begins: sampling bias, measurement error, missing data, proxy measurement, and ethical misuse. Oral clarification made the distinctions among precision, validity, and reliability especially important. | core |
| 1.5 Types of data | Continuous, categorical, and ordinal data are introduced as practically important distinctions for later model choice. The lecture also signals that how a variable is treated can partly be an analytic decision. | important |
| 1.6 Probability and uncertainty | Probability is introduced as the logic of uncertainty. A central distinction is made between aleatory uncertainty in the world and epistemic uncertainty from incomplete knowledge. | core |
| 1.7 Probability distributions | Distributions are introduced as structured representations of possible values, with an explicit distinction between discrete probabilities and continuous densities. The notebook and minutes make PDF/CDF interpretation and sample-vs-distribution distinctions more important than the bare slide text alone suggests. | core |
| 1.8 Parameters and describing distributions | The lecture shows how distributions can be summarized by center, spread, asymmetry, and tail behavior. Notebook figures materially deepen interpretation of mean/median/mode, skewness, and especially kurtosis. | core |
| 1.9 About this course | Course goals, tools, grading, and resources are outlined. This segment matters for orientation, not for direct conceptual assessment of lecture content. | brief |

## 3. Core mastery topics

### T1. Statistics as indirect reasoning about reality through data and models
- **Importance:** core
- **Concise description:** The student understands that statistics does not read truth directly from the world. It uses data to evaluate and revise models of processes that generated the observations.
- **What successful understanding looks like:** The student can explain the distinct roles of reality, data, and models, and can describe why statistics constrains explanations without guaranteeing truth.
- **Common confusion or near-miss likely for this lecture:** Talking as if data or a fitted model directly reveal reality, or treating the reality–data–model diagram as mere lecture framing rather than the core inferential structure.

### T2. What counts as data: measurement, processing, and finiteness
- **Importance:** core
- **Concise description:** The student understands data as finite recorded outputs of measurement processes, including processed or derived quantities when those remain part of the evidence pipeline.
- **What successful understanding looks like:** The student can explain why data are not raw reality, why processed quantities can still count as data, and why the finiteness of the current dataset matters for inference.
- **Common confusion or near-miss likely for this lecture:** Treating only raw measurements as “real data,” or speaking as if the possibility of collecting more data makes the current dataset effectively unlimited.

### T3. Imperfect data and measurement quality
- **Importance:** core
- **Concise description:** The student can distinguish important forms of imperfection in data collection and interpretation, especially precision, validity, reliability, sampling bias, missing data, proxy measurement, and ethical responsibility.
- **What successful understanding looks like:** The student can separate these failure modes conceptually and explain why some problems cannot be fixed just by later statistical analysis.
- **Common confusion or near-miss likely for this lecture:** Using the terms precision, validity, and reliability interchangeably; treating missing data as only a loss of sample size; or speaking as if a proxy is the same thing as the target construct.

### T4. Data types and analytic treatment
- **Importance:** important
- **Concise description:** The student recognizes continuous, categorical, and ordinal data and understands that data type matters for later modeling, while also recognizing that treatment of a variable can sometimes be a pragmatic modeling choice.
- **What successful understanding looks like:** The student can classify examples, justify borderline cases, and explain why mixed-type datasets are common.
- **Common confusion or near-miss likely for this lecture:** Treating type assignment as purely automatic and consequence-free, or failing to distinguish ordinal from continuous treatment.

### T5. Probability as a language for uncertainty
- **Importance:** core
- **Concise description:** The student understands why probability is needed once data are imperfect and models leave uncertainty, and can distinguish aleatory uncertainty from epistemic uncertainty.
- **What successful understanding looks like:** The student can explain both uncertainty types, show how they differ, and connect them to the kinds of examples used in lecture.
- **Common confusion or near-miss likely for this lecture:** Using long-run frequency language for all probability statements, including one-off predictive cases that the lecture treated as epistemic.

### T6. Probability distributions and how to read them
- **Importance:** core
- **Concise description:** The student understands a probability distribution as a structured description of possible values for a variable, including the distinction between discrete probability and continuous density, and between a distribution and samples drawn from it.
- **What successful understanding looks like:** The student can interpret random variables, discrete vs. continuous cases, PDF vs. CDF, and interval probability in a conceptually correct way.
- **Common confusion or near-miss likely for this lecture:** Treating the height of a continuous PDF at a point as a point probability, or confusing a simulated histogram with the underlying distribution itself.

### T7. Parameters and descriptive summaries of distributions
- **Importance:** core
- **Concise description:** The student understands how distributions can be described by center, spread, asymmetry, modality, and tail behavior, and why different summaries answer different descriptive questions.
- **What successful understanding looks like:** The student can interpret mean, median, mode, spread measures, skewness, and kurtosis in relation to the shape of a distribution.
- **Common confusion or near-miss likely for this lecture:** Treating one summary as sufficient for the whole distribution, equating heavier tails with merely larger standard deviation, or repeating formula language without being able to interpret the plots.

## 4. Elements within topics

### T1. Statistics as indirect reasoning about reality through data and models

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Reality, data, and models are distinct | Reality is what we care about; data are what we observe; models connect the two. | This is the lecture’s basic inferential scaffold. | slides / handout + instructional minutes |
| Models are the bridge, not an optional extra | Measurements become informative only through a model of the generating process. | This is the criterion for what statistics is doing here. | slides / handout + instructional minutes |
| Statistical conclusions are constrained, not guaranteed | Data can support or weaken models without proving one true. | This is the central caution attached to statistical reasoning. | slides / handout + instructional minutes |
| The discovery loop is iterative | Data inform models, models guide new experiments, and the cycle repeats. | The lecture frames inference as an update loop rather than a one-shot deduction. | slides / handout |

### T2. What counts as data: measurement, processing, and finiteness

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Data are recorded outputs of measurement | Data come from measurement processes, not from direct access to reality. | This defines what data are in this lecture. | slides / handout |
| Processed quantities can still be data | Normalized, aggregated, or extracted quantities may still function as data. | This lecture explicitly treats processing as part of the evidence pipeline. | slides / handout + notebook + instructional minutes |
| Data are finite at the moment of analysis | Even if more could be collected later, the current dataset is bounded. | The finiteness claim matters because later inference works from the data actually in hand. | slides / handout + instructional minutes |
| Measurement pipeline matters for interpretation | A number cannot be interpreted well without knowing how it was produced. | This ties the concept of data to scientific interpretation. | slides / handout + notebook |

### T3. Imperfect data and measurement quality

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Precision, validity, and reliability are different | Consistency, measuring the intended thing, and stability across repetitions/raters are not the same issue. | This was one of the lecture’s most important distinction-heavy areas. | slides / handout + notebook + instructional minutes |
| Sampling bias | The dataset can systematically misrepresent the population or use setting. | This is a core way data can fail before modeling. | slides / handout + instructional minutes |
| Measurement error | The recorded value can differ from the target value in a practically important way. | This is another primary data-quality failure mode. | slides / handout + instructional minutes |
| Missing data can bias, not just weaken precision | Absence of observations can distort conclusions, not merely widen uncertainty. | The minutes sharpened this beyond the bare slide bullet. | slides / handout + instructional minutes |
| Proxy measures are indirect stand-ins | Some measurements are only imperfect indicators of the true construct of interest. | This is a recurring scientific problem explicitly emphasized in the lecture. | slides / handout + instructional minutes |
| Ethical responsibility is tied to data use | Data quality and data ethics are linked when data affect people. | The lecture treats ethics as part of responsible inference, not as a separate afterthought. | slides / handout |

### T4. Data types and analytic treatment

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Continuous data | Numerical values vary over a scale. | One of the main data-type categories introduced. | slides / handout + notebook |
| Categorical data | Values indicate group membership without numerical continuity. | Another main data-type category introduced. | slides / handout + notebook |
| Ordinal data | Categories have order but not full continuous structure. | This is where the lecture’s most interesting borderline treatment issue appears. | slides / handout + instructional minutes |
| Mixed-type datasets are normal | Real biomedical datasets often combine several data types. | This supports later model-choice reasoning. | slides / handout + notebook + instructional minutes |
| Treatment can be a modeling choice | Some variables, especially highly graded ordinal ones, may be treated pragmatically. | The minutes made this more important than a static definition-only reading would. | instructional minutes |

### T5. Probability as a language for uncertainty

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Probability enters because uncertainty is unavoidable | Imperfect data and stochastic modeling require a language of uncertainty. | This is the bridge from the data sections into probability. | slides / handout |
| Aleatory uncertainty | Some uncertainty comes from randomness in the process itself. | One half of the lecture’s core uncertainty split. | slides / handout + notebook + instructional minutes |
| Epistemic uncertainty | Some uncertainty comes from incomplete or uneven knowledge. | The other half of the core uncertainty split. | slides / handout + notebook + instructional minutes |
| Probability meaning depends on context | Repeated-trial frequency works naturally in some settings but not all. | This is the major interpretive warning in the section. | slides / handout + instructional minutes |
| More information changes some uncertainty but not all | Epistemic uncertainty can shrink with information; aleatory uncertainty is not eliminated that way. | This is the practical consequence of the distinction. | instructional minutes |

### T6. Probability distributions and how to read them

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Distribution as possibilities over values | A distribution represents possible values and how probability or density is allocated across them. | This is the topic’s defining idea. | slides / handout |
| Random variables: discrete vs. continuous | Discrete variables attach probability to values; continuous variables use density over ranges. | This is the lecture’s first major technical distinction in reading distributions. | slides / handout + notebook + instructional minutes |
| Sample vs. distribution | A dataset drawn from a distribution is not identical to the distribution that generated it. | The notebook demonstration makes this concretely visible. | notebook + instructional minutes |
| PDF vs. CDF | Density and cumulative probability are different objects with different uses. | This was made much more probe-worthy by the minutes and plots. | slides / handout + notebook + instructional minutes |
| Interval probability in the continuous case | Probability over a range comes from area or CDF differences, not from a single-point height. | This is one of the lecture’s clearest sound-right-but-wrong traps. | notebook + instructional minutes |

### T7. Parameters and descriptive summaries of distributions

| Element | Concise description | Why it belongs inside this topic | Especially important by |
|---|---|---|---|
| Mean, median, and mode answer different “middle” questions | Different notions of center can diverge in asymmetric distributions. | This is the first central descriptive contrast in the topic. | slides / handout + notebook + instructional minutes |
| Center and spread as a two-number description | A distribution can often be summarized by location plus dispersion, while remaining an approximation. | This is the topic’s core compression idea. | slides / handout + notebook |
| Different spread summaries capture different notions | Standard deviation, variance, absolute deviation, and interquartile range are not interchangeable labels. | The lecture introduces multiple spread summaries explicitly. | slides / handout + notebook |
| Modality | A distribution may have one mode or more than one, with multimodality often suggesting mixed sources. | This belongs here because it concerns shape beyond simple center/spread. | slides / handout + notebook |
| Skewness | Asymmetry is about direction of the long tail, not just “not normal.” | This is a core shape descriptor in the section. | slides / handout + notebook + instructional minutes |
| Kurtosis | Tail behavior relative to a normal baseline can differ even when spread is matched. | The notebook and minutes made this considerably more important than the slide bullet alone. | slides / handout + notebook + instructional minutes |

## 5. Evidence standards

**Calibration for this section:** “Full evidence” means enough evidence for the topic to count as solidly understood for session purposes. It does **not** mean exhaustive or perfect mastery. Stronger transfer, better synthesis, clearer independence, and more robust cross-checking can still raise confidence beyond that threshold.

### T1. Statistics as indirect reasoning about reality through data and models
- **Full evidence:** The student clearly distinguishes reality, data, and models; explains that data inform models about reality rather than revealing truth directly; and can say why more than one model may fit the same data or why the loop continues through further experiments.
- **Partial evidence:** The student says that statistics uses data to learn about reality and mentions models, but the explanation remains generic or under-justified.
- **Weak or no evidence:** The student treats data as direct truth, treats a model as a mere graph/formula with no inferential role, or cannot explain why statistics is needed.
- **Echoed or assisted evidence:** Repeating “reality, data, and models” after the tutor names them, without explaining their roles.
- **Genuinely student-owned evidence:** Explaining in the student’s own words why measurements alone are not enough and what the model contributes.
- **Fresh check or transfer that raises confidence:** Applying the reality–data–model distinction to a new biomedical example or explaining why good data still do not prove one model true.
- **Especially important near-misses:** “The data tell us reality directly”; “if the model fits, it is true.”
- **Vulnerability to sounding right without understanding:** High.
- **Mastery progression cues:** 1) recognizes that statistics deals with data; 2) notes data are not reality; 3) states a usable role for models; 4) explains the three-part relation in one case; 5) gives a student-owned account of indirect inference; 6) handles a second probe about uncertainty or model competition; 7) transfers the idea to a new experiment; 8) synthesizes the iterative loop without collapsing model fit into truth.

### T2. What counts as data: measurement, processing, and finiteness
- **Full evidence:** The student explains that data are finite recorded outputs of measurement, not reality itself, and can correctly defend at least one processed or derived quantity as still counting as data when it remains part of the evidence pipeline.
- **Partial evidence:** The student identifies data as measurements and may mention finiteness or processing, but cannot explain why those points matter.
- **Weak or no evidence:** The student treats only raw measurements as real data, or cannot distinguish the measured quantity from the underlying phenomenon.
- **Echoed or assisted evidence:** Agreeing that “normalized data are still data” without being able to justify why.
- **Genuinely student-owned evidence:** Explaining why normalized cerebellar volume or another derived quantity can be more informative for the scientific comparison of interest.
- **Fresh check or transfer that raises confidence:** Classifying a new processed feature, averaged signal, or normalized measure and explaining whether it still counts as data.
- **Especially important near-misses:** “Derived values are not data anymore”; “data are effectively infinite because we could always measure more.”
- **Vulnerability to sounding right without understanding:** Moderate.
- **Mastery progression cues:** 1) identifies data as measurements; 2) notes that data are recorded rather than identical to reality; 3) accepts that processing can occur; 4) explains a concrete processed-data example; 5) explains why finiteness matters; 6) handles a second example without prompting; 7) connects measurement pipeline to interpretation quality; 8) integrates raw, derived, and finite-data ideas into one coherent account.

### T3. Imperfect data and measurement quality
- **Full evidence:** The student can correctly distinguish at least two major data-quality failures, including the precision/validity/reliability trio or a clear contrast such as missing data vs. measurement error, and can explain why the distinction matters for inference.
- **Partial evidence:** The student knows some labels and can gesture toward “bad data,” but blurs the distinctions or gives only one shallow example.
- **Weak or no evidence:** The student uses the major terms interchangeably, treats missing data as only reduced sample size, or assumes later statistics can rescue fundamentally misaligned measurement.
- **Echoed or assisted evidence:** Copying the tutor’s corrected labels without being able to classify a fresh example.
- **Genuinely student-owned evidence:** Correctly diagnosing a new example and saying what kind of inferential risk it creates.
- **Fresh check or transfer that raises confidence:** Sorting a new case into precision, validity, reliability, sampling bias, missingness, or proxy measurement and defending the choice.
- **Especially important near-misses:** “Reliable means valid”; “missing data only increases variance”; “a proxy is just the thing itself measured differently.”
- **Vulnerability to sounding right without understanding:** Very high.
- **Mastery progression cues:** 1) recognizes that data can fail in multiple ways; 2) names one distinction correctly; 3) explains one distinction in own words; 4) applies it to a lecture-like example; 5) separates two nearby failure modes independently; 6) handles a second fresh case; 7) explains why statistics cannot fully repair some failures; 8) synthesizes data quality, proxy caution, and inferential consequences clearly.

### T4. Data types and analytic treatment
- **Full evidence:** The student can classify variables as continuous, categorical, or ordinal, explain a borderline case, and show awareness that type treatment can sometimes reflect a modeling decision rather than a purely ontological fact.
- **Partial evidence:** The student can classify obvious cases but struggles with ordinal variables or mixed datasets.
- **Weak or no evidence:** The student misclassifies basic examples or treats every variable as having one forced type with no analytic consequences.
- **Echoed or assisted evidence:** Repeating the three labels without being able to justify a classification.
- **Genuinely student-owned evidence:** Defending why an ordinal variable might sometimes be treated as continuous while noting the simplification involved.
- **Fresh check or transfer that raises confidence:** Classifying a new small dataset and explaining one modeling consequence of the type choices.
- **Especially important near-misses:** Treating ordinal variables as automatically continuous or treating type recoding as inconsequential.
- **Vulnerability to sounding right without understanding:** Moderate.
- **Mastery progression cues:** 1) recalls the three broad types; 2) classifies obvious examples; 3) explains one borderline distinction; 4) handles a mixed dataset; 5) recognizes treatment as a modeling choice in some cases; 6) justifies that choice on a new example; 7) connects type to downstream model suitability; 8) compares two plausible treatments without collapsing them into “anything goes.”

### T5. Probability as a language for uncertainty
- **Full evidence:** The student explains why probability is needed in this lecture and can clearly distinguish aleatory from epistemic uncertainty, including how information changes one more naturally than the other.
- **Partial evidence:** The student remembers the two labels or one example, but cannot articulate the distinction cleanly or overextends one interpretation to all probability.
- **Weak or no evidence:** The student reduces all probability to repeated trials, or cannot explain what epistemic uncertainty adds.
- **Echoed or assisted evidence:** Repeating “aleatory is randomness, epistemic is lack of knowledge” without being able to classify an example or explain the consequence.
- **Genuinely student-owned evidence:** Using the roulette / poker / prediction example logic correctly in new words.
- **Fresh check or transfer that raises confidence:** Sorting a new scenario into mostly aleatory, mostly epistemic, or mixed, and defending the judgment.
- **Especially important near-misses:** “All probabilities are long-run frequencies”; “more information removes aleatory randomness from the process.”
- **Vulnerability to sounding right without understanding:** High.
- **Mastery progression cues:** 1) links probability to uncertainty; 2) names the two uncertainty types; 3) gives one correct example; 4) explains the distinction in own words; 5) classifies a fresh case; 6) explains what more information can and cannot change; 7) connects the distinction back to scientific modeling; 8) handles mixed cases without flattening everything into one interpretation.

### T6. Probability distributions and how to read them
- **Full evidence:** The student can explain what a distribution represents, distinguish discrete probabilities from continuous densities, and correctly interpret either interval probability via the CDF or the difference between a sample histogram and the underlying distribution.
- **Partial evidence:** The student knows that a distribution describes uncertainty and may name PDF/CDF, but cannot interpret them correctly or confuses density with point probability.
- **Weak or no evidence:** The student treats a continuous PDF height as the probability at a point, or treats simulated data as the same object as the distribution.
- **Echoed or assisted evidence:** Repeating “CDF is cumulative” without explaining what is accumulating or how it helps compute a probability.
- **Genuinely student-owned evidence:** Explaining why probability between -2 and 0 comes from area or CDF difference rather than from reading a single y-value on the PDF.
- **Fresh check or transfer that raises confidence:** Interpreting a new PDF/CDF panel, or explaining what changes and what stays fixed when a distribution generates new samples.
- **Especially important near-misses:** “The PDF value is the probability of that exact continuous value”; “the histogram is the probability distribution.”
- **Vulnerability to sounding right without understanding:** Very high.
- **Mastery progression cues:** 1) recognizes a distribution as a map of possibilities; 2) distinguishes discrete from continuous in broad terms; 3) states that continuous probability lives over ranges; 4) explains one PDF/CDF relation; 5) interprets a notebook plot correctly; 6) distinguishes sample from generating distribution on a second probe; 7) handles interval probability independently; 8) flexibly interprets multiple representation forms without mixing their meanings.

### T7. Parameters and descriptive summaries of distributions
- **Full evidence:** The student can interpret at least one center distinction and one shape or spread distinction correctly, such as mean vs. median in a skewed distribution or kurtosis vs. standard deviation when spread is matched.
- **Partial evidence:** The student can name summaries and perhaps define one, but cannot interpret what a change in shape would do to those summaries.
- **Weak or no evidence:** The student treats one summary as fully characterizing the distribution, confuses skewness with spread, or explains kurtosis only as “pointiness” with no tail interpretation.
- **Echoed or assisted evidence:** Repeating that “mean, median, and mode are different” or that “kurtosis is tail weight” without being able to read a plot.
- **Genuinely student-owned evidence:** Explaining where mean, median, and mode would lie in a skewed distribution or why same-variance distributions can still differ in kurtosis.
- **Fresh check or transfer that raises confidence:** Interpreting a new plot with skew, multimodality, or heavy tails, or choosing which summary would be most informative for a stated descriptive purpose.
- **Especially important near-misses:** “Heavier tails just means larger standard deviation”; “median is always the best center”; “kurtosis is only peak sharpness.”
- **Vulnerability to sounding right without understanding:** High.
- **Mastery progression cues:** 1) identifies a common summary measure; 2) distinguishes center from spread; 3) explains one center measure in own words; 4) interprets a skewed example; 5) explains one shape descriptor beyond center/spread; 6) handles a second plot or summary contrast; 7) explains why matched spread need not imply matched kurtosis; 8) integrates center, spread, skewness, and tails into a coherent description of distribution shape.

## 6. Grade structure

- A topic should count as **meaningfully mastered / solidly understood** when the student has shown enough conceptually correct, mostly student-owned evidence for that topic to meet the **Full evidence** standard above. This may occur without exhaustive coverage of every element inside the topic.
- Lecture-wide grading should reflect increasing **breadth of solidly understood topics**, not raw element count and not isolated buzzwords.
- Grading should reflect the **best demonstrated mastery so far**. Later turns may strengthen confidence in a topic, but weaker later performance should not erase earlier solid evidence.
- Material that has not been covered in the session should count as **not yet demonstrated**, not as implicitly known.
- Vague label-matching, tutor-echoing, or surface wording without usable explanation should not count as strong evidence.
- Assisted answers can establish **partial evidence**, but independent explanation, correct interpretation of a fresh representation, and transfer to a nearby new case are stronger evidence.
- Later refinement on a topic can strengthen confidence, but it is not the only way a topic can count as solidly understood. A topic can already count once the student has clearly crossed the “Full evidence” threshold.
- Brief topics should not dominate the lecture-wide picture. Broad coverage should come mainly from the lecture’s core and important topics.

### Qualitative lecture-wide coverage anchors

| Coverage anchor | Qualitative meaning |
|---|---|
| Strong foothold in one central lecture idea | The student has one clearly understood core topic, with the rest still mostly untested or tentative. |
| Meaningful early coverage across the lecture | The student has partial-to-solid understanding in more than one area and is no longer confined to a single isolated idea. |
| Solid grounding across the core lecture terrain | Several core topics have reached solid understanding, with only limited weak spots among the major ideas. |
| Broad and competent coverage | Most of the major lecture terrain is covered with usable understanding, even if some finer distinctions remain shaky. |
| Very broad coverage with only small gaps remaining | Nearly all major topics are solid, and remaining weaknesses are narrow or brief-material gaps. |
| Full lecture mastery for session purposes | The student has demonstrated broad, conceptually reliable command of the lecture’s main assessed topics, including at least some genuine interpretation or transfer rather than memorized wording alone. |

## 7. Good question forms for this lecture

### Best question forms
- **Forced distinction:** “How is validity different from reliability?” “What is the difference between aleatory and epistemic uncertainty?”
- **Classification with justification:** “Is this variable continuous, ordinal, or categorical, and why?” “Is this mainly a sampling-bias problem or a measurement-error problem?”
- **Figure interpretation:** Reality–data–model diagram; running proportion of heads plot; PDF/CDF panels; gamma plot with mean/median/mode; skewness and kurtosis comparison panels.
- **Code or plot interpretation:** “What does the shaded region under the Normal curve mean?” “What is the histogram showing relative to the binomial PMF?”
- **Choosing between two plausible alternatives:** “Which summary is being pulled by the long right tail?” “Does more information change the probability here because the process changed or because knowledge changed?”
- **One-sentence correction:** “What is wrong with saying the PDF value at one point is the probability of that exact value?”
- **One-sentence explanation:** “Why can normalized cerebellar volume still count as data?”
- **Apply to a nearby new case:** Give a new biomedical measurement, prediction, or distribution plot and ask the student to classify or interpret it.
- **Explain why an example fits one concept and not another:** “Why is calcium imaging a proxy measure rather than direct measurement of neural activity?”

### Use sparingly or avoid
- Pure recall of historical names, dates, paper citations, package names, or slide titles.
- Questions whose only correct answer is an exact phrase from class.
- Long derivation prompts about formulas for moments.
- Questions about exact Polymarket prices, war specifics, or other local details of the example.
- “What did the professor say about...?” questions.
- Transcript-memory questions.
- Wording-recall questions unless the wording itself carries a conceptual distinction.
- Course-logistics questions from section 1.9 as evidence of lecture mastery.

## 8. Report-ready mastery labels

| Topic | Mastered label | Partial label | Missing label |
|---|---|---|---|
| T1 Statistics as indirect reasoning about reality through data and models | Clear grasp of the reality–data–model logic | Partial grasp of how data and models relate | No usable grasp of the reality–data–model logic yet |
| T2 What counts as data: measurement, processing, and finiteness | Understands what counts as data in this lecture | Partial understanding of data as measurement output | No clear understanding yet of what counts as data |
| T3 Imperfect data and measurement quality | Distinguishes key data-quality failures well | Partial distinction among data-quality issues | No reliable distinction yet among the major data-quality issues |
| T4 Data types and analytic treatment | Classifies data types and borderline cases well | Partial understanding of data-type distinctions | No clear grasp yet of the main data-type distinctions |
| T5 Probability as a language for uncertainty | Clear distinction between aleatory and epistemic uncertainty | Partial grasp of uncertainty types | No clear distinction yet between the lecture’s uncertainty types |
| T6 Probability distributions and how to read them | Interprets distributions, density, and cumulative probability well | Partial understanding of how to read distributions | No clear understanding yet of how distributions are being interpreted |
| T7 Parameters and descriptive summaries of distributions | Interprets center, spread, and shape summaries well | Partial understanding of distribution summaries | No clear understanding yet of the lecture’s distribution summaries |

## 9. Rubric use notes

- **What the lecture seems to care about most:** The lecture cares most about conceptual interpretation: how data relate to reality through models, how measurement can fail, how probability represents uncertainty, and how distributions should be read rather than merely named.
- **Where the lecture is vulnerable to superficial regurgitation:** T1, T3, T5, T6, and T7 are all vulnerable. Students can sound fluent by repeating labels like model, validity, epistemic, PDF, CDF, skewness, and kurtosis without being able to interpret a new example or representation.
- **Which topics need especially careful probing:** T3 and T6 need the most careful probing because nearby confusions are easy and important. T5 and T7 also need careful probing because students can memorize slogans that collapse under a fresh case.
- **How much fidelity to slide wording matters versus fidelity to concepts:** Fidelity to concepts matters much more. Short, imperfect wording should count when the distinction or interpretation is clear. Exact slide phrasing should matter only when it carries a genuine conceptual contrast.
- **Which important clarifications came mainly from oral explanation rather than the static materials:** The minutes materially sharpened the non-decorative status of the reality–data–model diagram, the processed-and-still-data point, the distinction among precision/validity/reliability, the fact that missing data may bias rather than merely increase variance, the aleatory/epistemic contrast, the PDF-vs-CDF interpretation, and the kurtosis-vs-spread distinction.
- **Whether the notebook materially changes what should count as mastery:** Yes. The notebook makes figure and code interpretation part of mastery for T3, T4, T6, and especially T7. In particular, the histogram-vs-PMF comparison, shaded Normal interval, PDF/CDF panels, mean-median-mode gamma plot, and standardized skewness/kurtosis comparisons turn otherwise static terms into interpretive targets.
- **Whether the minutes revealed hidden depth that should influence questioning:** Yes. The minutes show that this lecture was not just definitional. Several topics were orally deepened into probe-worthy distinctions, and the rubric should treat those distinctions as central evidence targets rather than optional enrichment.
- **Short-session note:** This is a broad lecture, but a review session should stay short. The right goal is not to exhaust every element. It is to establish solid understanding in a meaningful spread of topics, using the elements as focused probes rather than as a checklist.
