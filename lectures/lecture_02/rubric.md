# Mastery Rubric

## 1. Lecture metadata

* **Lecture title:** Lecture 2: Models
* **Lecture number or identifier:** Statistics 367-1-4361, Lecture 2
* **Source files used:** `Lecture 2 Models.pptx`, `Lecture-2-handout.pdf`, `Lecture02_Models.ipynb`
* **Main purpose of the lecture:** To introduce statistical models as generative accounts of data, derive Bayesian updating from conditional probability, build intuition for likelihood, prior, posterior, grid-based computation, Beta-Binomial conjugacy, and prior choice, and briefly motivate prior elicitation with Preliz and the later move from grids to sampling.  

## 2. Lecture map

| Section / segment               | Summary                                                                                                                                                                                        | Relative importance |     |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | --- |
| 2.1 What is a statistical model | A model is presented as an explicit probabilistic idea of how data could have been generated. The lecture contrasts model-based thinking with a narrower estimator-focused view of statistics. | core                |     |
| 2.2 Conditional probability     | Reviews joint, marginal, and conditional probability, with emphasis that conditioning has direction and that reversing conditionals is a substantive mistake.                                  | core                |     |
| 2.3 Bayes rule                  | Converts conditional probability into the main update rule of the course and names the key pieces: prior, likelihood, posterior, evidence.                                                     | core                |     |
| 2.4 Likelihood                  | Uses the coin-flip example and Binomial model to define likelihood as probability of the observed data as a function of the parameter.                                                         | core                |     |
| 2.5 Grid calculation            | Shows posterior computation by evaluating prior and likelihood on a dense grid, multiplying pointwise, then normalizing.                                                                       | important           |     |
| 2.6 Prior                       | Frames the prior as a proper probability distribution over parameter values and stresses that priors matter especially when data are limited.                                                  | core                |     |
| 2.7 Beta distribution           | Introduces Beta as a flexible prior family for probabilities, with shape controlled by (\alpha,\beta).                                                                                         | important           |     |
| 2.8 Conjugate priors            | Shows Beta-Binomial conjugacy, proportional reasoning in derivations, and pseudo-count interpretation.                                                                                         | core                |     |
| 2.9 Posterior distribution      | Emphasizes that the posterior is a distribution, that uncertainty shrinks with more data, priors matter less as data accumulate, and order does not matter here.                               | core                |     |
| 2.10 Choosing priors            | Surveys kinds of priors and argues that prior choice should depend on the scientific problem and available background knowledge.                                                               | important           |     |
| 2.11 Preliz                     | Introduces Preliz and `maxent` as practical tools for exploring distributions and eliciting priors from constraints.                                                                           | brief               |     |
| 2.12 Next week                  | Notes that grid methods are pedagogically useful but do not scale, motivating sampling and PyMC.                                                                                               | brief               |     |

## 3. Core mastery targets

1. **Statistical model as generative explanation**

   * **Description:** Understand that a statistical model is an explicit probabilistic account of how data could arise, not just a machine for producing estimates.
   * **Importance:** core
   * **Successful understanding looks like:** Student can explain that the model specifies distributions and parameters and that data update the model or beliefs within it.
   * **Common confusion or near-miss:** Treating the model as just a formula for an estimator or as a summary of data rather than a generative account.

2. **Direction of conditioning**

   * **Description:** Distinguish joint, marginal, and conditional probability, especially that (p(a\mid b)) and (p(b\mid a)) are not interchangeable.
   * **Importance:** core
   * **Successful understanding looks like:** Student can classify statements or formulas correctly and explain what is being conditioned on.
   * **Common confusion or near-miss:** Reversing the conditional or speaking as if direction is cosmetic.

3. **Bayes rule as model updating**

   * **Description:** Understand Bayes rule as the rule that updates beliefs about parameters after data.
   * **Importance:** core
   * **Successful understanding looks like:** Student can identify prior, likelihood, posterior, and evidence and describe their roles.
   * **Common confusion or near-miss:** Saying the likelihood is “the probability of the parameter” or treating evidence as optional decoration rather than normalization.

4. **Likelihood as function of parameter given fixed data**

   * **Description:** Understand likelihood in the coin/Binomial example as the probability of the observed data viewed as a function of (\theta).
   * **Importance:** core
   * **Successful understanding looks like:** Student can say what changes and what stays fixed, and can interpret a likelihood curve as relative support for parameter values.
   * **Common confusion or near-miss:** Describing likelihood as a probability distribution over (\theta).

5. **Posterior from prior × likelihood + normalization**

   * **Description:** Understand the computational logic of posterior construction on a grid.
   * **Importance:** important
   * **Successful understanding looks like:** Student can explain evaluate → multiply → normalize, and why normalization is needed.
   * **Common confusion or near-miss:** Thinking normalization happens before multiplication, or not recognizing that the unnormalized product is not yet a proper distribution.

6. **Prior as proper probability distribution over plausible parameter values**

   * **Description:** Understand what a prior is and why it must integrate to 1.
   * **Importance:** core
   * **Successful understanding looks like:** Student can describe the prior as encoding parameter uncertainty or plausibility before the current data.
   * **Common confusion or near-miss:** Treating the prior as arbitrary bias only, or as something that need not be a probability distribution.

7. **Beta distribution as a prior family for probabilities**

   * **Description:** Understand why Beta is useful for (\theta \in [0,1]) and how (\alpha,\beta) shape the prior.
   * **Importance:** important
   * **Successful understanding looks like:** Student can explain range-matching and flexibility, and can interpret broad vs narrow or skewed Beta shapes.
   * **Common confusion or near-miss:** Memorizing the formula without understanding why Beta fits coin-flip probabilities.

8. **Conjugacy and pseudo-count intuition**

   * **Description:** Understand that Beta prior + Binomial likelihood yields Beta posterior, and that the update can be interpreted through added heads/tails.
   * **Importance:** core
   * **Successful understanding looks like:** Student can state the updated parameters and explain pseudo-count intuition without overclaiming it.
   * **Common confusion or near-miss:** Remembering “Beta stays Beta” but not knowing what actually updates.

9. **Posterior as distribution, not just point estimate**

   * **Description:** Understand that Bayesian analysis yields a full posterior whose spread reflects uncertainty.
   * **Importance:** core
   * **Successful understanding looks like:** Student can interpret narrowing posteriors with more data and explain why different priors converge.
   * **Common confusion or near-miss:** Reducing the posterior to “the answer” as a single best value only.

10. **Order-invariance in the Beta-Binomial example**

    * **Description:** Understand that in this model the final posterior depends on total heads and tails, not their order.
    * **Importance:** important
    * **Successful understanding looks like:** Student can say why different data orders with the same counts lead to the same final posterior here.
    * **Common confusion or near-miss:** Thinking Bayesian updating always depends on sequence in this example.

11. **Choosing priors as a modeling decision**

    * **Description:** Understand that prior choice depends on problem context and available knowledge, not on a single universally correct rule.
    * **Importance:** important
    * **Successful understanding looks like:** Student can distinguish weak, strong, empirical, weakly informative, and elicited priors at a practical level.
    * **Common confusion or near-miss:** Treating “vague” as automatically better or “objective” as automatically correct.

12. **Preliz as a practical elicitation tool**

    * **Description:** Understand the role of Preliz and `maxent` in constructing a prior from intuitive constraints.
    * **Importance:** brief
    * **Successful understanding looks like:** Student can explain what kind of input the tool uses and what it returns conceptually.
    * **Common confusion or near-miss:** Treating Preliz as a black box that removes the need to think about priors.     

## 4. Assessable target clusters for short sessions

### Cluster 1: Models, parameters, and conditioning

* **Included targets:** 1, 2
* **Why this cluster is coherent:** The lecture begins by shifting from estimator-thinking to generative model-thinking, then immediately gives the probabilistic language needed to talk about models correctly.
* **Best question types:** forced distinction, classification, one-sentence explanation, identifying what is wrong in a claim

### Cluster 2: Bayes rule and the roles of its parts

* **Included targets:** 3, 4
* **Why this cluster is coherent:** Bayes rule is the conceptual center of the lecture, and the likelihood is the most likely place where students confuse parameter-space and data-space reasoning.
* **Best question types:** choosing between two plausible alternatives, one-sentence correction, labeling parts of an expression, short interpretation

### Cluster 3: Building the posterior on a grid

* **Included targets:** 5, 9
* **Why this cluster is coherent:** This is the lecture’s main computational intuition-builder: posterior is not magic, but prior × likelihood followed by normalization, producing a distribution rather than just an estimate.
* **Best question types:** process ordering, figure interpretation, error detection, one-sentence explanation

### Cluster 4: Priors and Beta distributions

* **Included targets:** 6, 7
* **Why this cluster is coherent:** The lecture treats priors first conceptually, then gives Beta as the main practical family for probabilities.
* **Best question types:** comparison, classification, figure interpretation, choosing among plausible priors

### Cluster 5: Conjugacy and pseudo-count updating

* **Included targets:** 8, 10
* **Why this cluster is coherent:** This is the main algebraic payoff of the lecture and links symbolic updating to intuitive updating.
* **Best question types:** short derivation check, fill the update, explain a pseudo-count claim, identify whether order matters

### Cluster 6: Prior sensitivity, elicitation, and practical prior choice

* **Included targets:** 11, 12
* **Why this cluster is coherent:** These topics move from mechanics to judgment: when priors matter, how they are chosen, and how Preliz supports elicitation.
* **Best question types:** scenario judgment, comparison, one-sentence justification, tool interpretation

### Cluster 7: Limits of grid methods and transition to sampling

* **Included targets:** 5, 12 partly, plus lecture-close transition
* **Why this cluster is coherent:** This is the closing conceptual bridge: grid methods are useful for learning and small problems, but not scalable.
* **Best question types:** short comparison, identify the limitation, explain why sampling is introduced
* **Note:** This should usually be sampled lightly, since it is more of a bridge than a main mastery target.  

## 5. Evidence standards

### Cluster 1: Models, parameters, and conditioning

* **Full evidence:** Correctly distinguishes model vs estimator framing, and correctly explains or classifies conditional direction without reversing it.
* **Partial evidence:** Gets the general idea of models or conditional probability but uses vague language or makes one mild directional mistake.
* **Weak or no evidence:** Treats a model as just a fitted number-producing procedure, or treats (p(a\mid b)) and (p(b\mid a)) as interchangeable.

### Cluster 2: Bayes rule and the roles of its parts

* **Full evidence:** Correctly identifies prior, likelihood, posterior, evidence, and explains likelihood as data-given-parameter with fixed observed data.
* **Partial evidence:** Knows most labels but blurs likelihood vs posterior or gives only memorized wording without interpretation.
* **Weak or no evidence:** Says likelihood is the probability of the parameter, or cannot explain what is updated by Bayes rule.

### Cluster 3: Building the posterior on a grid

* **Full evidence:** Can state the grid procedure in the right order and explain why normalization is needed; also recognizes that the posterior remains a distribution.
* **Partial evidence:** Remembers multiply-and-normalize but cannot clearly say what is being normalized or what the result means.
* **Weak or no evidence:** Describes an incorrect procedure, or treats the computation as producing only a point estimate.

### Cluster 4: Priors and Beta distributions

* **Full evidence:** Explains prior as a proper probability distribution over plausible parameter values and explains why Beta is a natural family for probabilities in ([0,1]).
* **Partial evidence:** Recognizes Beta as common for probabilities but gives only superficial or formula-based reasons.
* **Weak or no evidence:** Cannot say what the prior represents, or gives no sensible reason Beta is used here.

### Cluster 5: Conjugacy and pseudo-count updating

* **Full evidence:** Correctly states the Beta-Binomial update and gives a reasonable pseudo-count interpretation, including that heads and tails update different parameters.
* **Partial evidence:** Knows that “Beta stays Beta” but cannot clearly state the parameter update or overstates pseudo-counts as literal prior data.
* **Weak or no evidence:** Cannot connect prior and posterior families or gives the wrong update direction.

### Cluster 6: Prior sensitivity, elicitation, and practical prior choice

* **Full evidence:** Explains that prior choice depends on context and background knowledge, and can describe what Preliz/`maxent` is doing conceptually.
* **Partial evidence:** Knows that priors matter more with less data, but gives shallow or slogan-level statements about choosing priors.
* **Weak or no evidence:** Claims vague priors are always best, or treats elicitation as irrelevant or purely automatic.

### Cluster 7: Limits of grid methods and transition to sampling

* **Full evidence:** Explains that grid methods are pedagogically useful for low-dimensional examples but break down in higher dimensions, motivating sampling.
* **Partial evidence:** Remembers that sampling comes later but cannot say why grids fail.
* **Weak or no evidence:** Gives no meaningful explanation of why the course moves beyond grids.   

## 6. Grade structure

### Suggested weighting across clusters

| Cluster                                                       | Weight |
| ------------------------------------------------------------- | -----: |
| 1. Models, parameters, and conditioning                       |     18 |
| 2. Bayes rule and the roles of its parts                      |     20 |
| 3. Building the posterior on a grid                           |     16 |
| 4. Priors and Beta distributions                              |     14 |
| 5. Conjugacy and pseudo-count updating                        |     16 |
| 6. Prior sensitivity, elicitation, and practical prior choice |     12 |
| 7. Limits of grid methods and transition to sampling          |      4 |

**Total = 100**

### Converting sampled-cluster performance into a session grade out of 100

For each assessed cluster, score:

* **Full evidence = 1.0**
* **Partial evidence = 0.6**
* **Weak/no evidence = 0.2**
* **Not assessed = uncovered**

Then:

1. Compute the weighted score over only the clusters actually assessed.
2. Rescale by the total weight of assessed clusters to get a **session grade out of 100**.
3. Report separately which clusters were **not yet sampled**.

This allows a short chat to produce a defensible session grade without pretending the whole lecture was checked.

### Additional grading rules

* **Best demonstrated mastery so far:** If the student later gives a clearer or more correct answer on a cluster, the cluster score should rise to the best level demonstrated so far.
* **Uncovered material:** Material not yet probed counts as **not yet demonstrated**, not as mastered.
* **Buzzword penalty:** Naming terms without showing the distinction they encode does not earn full credit.
* **Concept over wording:** Short, imperfect English can receive full credit if the conceptual distinction is clear.
* **Short-session practicality:** In a sub-10-minute review, the bot should usually assess 3-4 clusters, preferably including Cluster 2 and at least one of Clusters 3-5.  

## 7. Good question forms for this lecture

### Best question forms

* **Forced distinction:** “Is this about probability of data given parameter, or parameter given data?”
* **Classification:** “Is this joint, marginal, or conditional?”
* **Figure interpretation:** “Why do these three posteriors get closer as more coin flips arrive?”
* **Identifying what is wrong in a claim:** “What is wrong with saying the likelihood is a distribution over (\theta)?”
* **Choosing between plausible alternatives:** “Which part of Bayes rule changes when new data arrive?”
* **One-sentence correction:** “Correct this sentence with the smallest possible change.”
* **One-sentence explanation:** “Why is Beta a natural prior family here?”
* **Update reasoning:** “If you observed more heads, which Beta parameter changes?”
* **Order/process checking:** “What comes first in grid calculation: normalize or multiply?”

### Use sparingly

* Long free-response derivations
* Requests for exact slide wording
* Pure symbol regurgitation without interpretation
* Broad opinion questions about priors with no concrete scenario
* Heavy computation by hand
* Open-ended essay prompts about the history of priors

### Avoid

* Questions that can be answered by parroting “prior, likelihood, posterior” without distinguishing them
* Questions that reward only formula memory
* Questions that require polished English rather than conceptual clarity  

## 8. Report-ready mastery labels

### Cluster 1: Models, parameters, and conditioning

* **Mastered label:** Understands models and conditioning
* **Partial label:** Basic model idea, shaky conditioning
* **Missing label:** Does not yet distinguish model/conditioning concepts

### Cluster 2: Bayes rule and the roles of its parts

* **Mastered label:** Correctly interprets Bayes rule parts
* **Partial label:** Knows Bayes rule terms, some role confusion
* **Missing label:** Bayes rule components not yet understood

### Cluster 3: Building the posterior on a grid

* **Mastered label:** Understands grid-based posterior construction
* **Partial label:** Partial grasp of multiply-and-normalize logic
* **Missing label:** Cannot yet explain posterior construction

### Cluster 4: Priors and Beta distributions

* **Mastered label:** Understands priors and Beta intuition
* **Partial label:** Some prior/Beta intuition, still superficial
* **Missing label:** Prior/Beta role not yet clear

### Cluster 5: Conjugacy and pseudo-count updating

* **Mastered label:** Understands conjugate updating
* **Partial label:** Recognizes conjugacy, weak update intuition
* **Missing label:** Conjugate update not yet understood

### Cluster 6: Prior sensitivity, elicitation, and practical prior choice

* **Mastered label:** Can reason about prior choice
* **Partial label:** Some sense of prior choice, limited justification
* **Missing label:** Prior choice reasoning not yet demonstrated

### Cluster 7: Limits of grid methods and transition to sampling

* **Mastered label:** Understands why the course moves to sampling
* **Partial label:** Knows grids are limited, reason still vague
* **Missing label:** Transition beyond grids not yet understood

## 9. Rubric use notes

* **What the lecture seems to care about most:** The center of gravity is not the historical material or formula recital. It is the conceptual chain: model → conditional probability → Bayes rule → likelihood/prior/posterior roles → concrete posterior construction → Beta-Binomial updating.  
* **Where the lecture is vulnerable to superficial regurgitation:** Students can easily memorize the words prior/likelihood/posterior/evidence, “Beta is conjugate to Binomial,” and “posterior is prior times likelihood,” without actually understanding what is conditioned on, what is fixed, or why normalization is needed. Those are the main fake-mastery zones.  
* **Which targets need especially careful probing:**

  1. Likelihood vs posterior
  2. Direction of conditioning
  3. Prior as a probability distribution rather than mere bias
  4. Conjugacy as an update rule rather than a vocabulary item
  5. Posterior as a distribution rather than a point estimate
* **How much fidelity to slide wording matters versus fidelity to concepts:** Very little fidelity to wording is needed. This lecture should be graded mainly on conceptual discrimination and interpretation. A student should get full credit for a short, plain answer that correctly distinguishes close ideas even if the wording is rough.
* **Broad lecture, short assessment:** The lecture is broad, but a short review session should not try to cover everything. Sample a few clusters deeply enough to expose confusion rather than touching every heading shallowly.
* **Notebook emphasis:** The uploaded notebook appears to reinforce rather than materially change the lecture emphasis. It mainly operationalizes the same core ideas with code for grid normalization, prior sensitivity, repeated Beta-Binomial updating, and Preliz-based elicitation, so the bot should still prioritize the lecture’s conceptual structure over code syntax.

---

## 10. Machine-parseable topic index

### T1. Models, parameters, and conditioning

**Importance:** core

### T2. Bayes rule and the roles of its parts

**Importance:** core

### T3. Building the posterior on a grid

**Importance:** core

### T4. Priors and Beta distributions

**Importance:** core

### T5. Conjugacy and pseudo-count updating

**Importance:** core

### T6. Prior sensitivity, elicitation, and practical prior choice

**Importance:** important

### T7. Limits of grid methods and transition to sampling

**Importance:** brief
