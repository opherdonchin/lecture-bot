```{python}
#| label: setup
import sys
from pathlib import Path

QMD_DIR = Path.cwd()
sys.path.append(str(QMD_DIR))

from slide_helpers import LectureSlides

slides = LectureSlides.from_config(
    "Lecture 2 Models",
    qmd_dir=QMD_DIR,
    config_path=QMD_DIR / "handout_config.yml",
)
```

# Lecture Overview

Lecture 2 introduces **statistical models** as explicit ideas about how data are generated, then develops the Bayesian update from **conditional probability** to **Bayes' rule**. The lecture uses the coin-flip example to define the **likelihood**, shows how a posterior can be computed on a **grid**, and then introduces the **prior** and the **Beta distribution** as a useful prior family for probabilities. It shows how Beta and Binomial models combine analytically through **conjugacy**, how posteriors evolve as data accumulate, and why prior choice matters. The lecture ends by introducing **Preliz** as a practical tool for prior elicitation and pointing ahead to sampling methods beyond grid calculations.

# Lecture Sections

## 2.1 — What Is a Statistical Model

This section introduces a statistical model as an explicit account of how data could have been generated. The slides contrast a period when statistics focused mainly on **estimators** with a return to models as scientific representations that can be updated by evidence. The central idea is that a model contains **probability distributions** and **parameters**, and that data analysis is not only about producing estimates but about revising a generative explanation in light of new evidence.

**New Definitions and Terms**

- **Statistical model** — a formal probabilistic account of how observed data could be generated
- **Parameter** — a quantity that determines the specific form of a probability distribution
- **Estimator** — a rule for producing a numerical guess for a parameter from data

```{python}
#| output: asis
print(slides.figure("A statistical model is an idea of how data could be generated"))
```

## 2.2 — Conditional Probability

This section reviews how probabilities change when we condition on additional information. The lecture distinguishes **joint**, **marginal**, and **conditional** probabilities, and emphasizes that conditioning has a direction: $p(r \mid c)$ and $p(c \mid r)$ are generally different. The section ends by connecting this idea to modeling, where we condition data on parameters and later condition parameters on data.

**New Definitions and Terms**

- **Joint probability** — the probability of two variables or events considered together
- **Marginal probability** — the probability of one variable after ignoring or summing over the other
- **Conditional probability** — the probability of one variable given information about another

**Formulas**

$$
P(A \mid B) = \frac{P(A, B)}{P(B)}
$$

Conditional probability is the joint probability, normalized by the probability of the condition.

```{python}
#| output: asis
print(slides.figure("Joint probability is the probability of more than one variable"))
```

## 2.3 — Bayes rule

This section turns conditional probability into the main updating rule of the course. Bayes' rule is introduced as the way to revise a model after observing data, and the lecture names the four parts that will be used repeatedly: **prior**, **likelihood**, **posterior**, and **evidence**. The slides also emphasize that Bayesian updating can feel counterintuitive at first, because we are learning about parameters indirectly through their consequences for the data.

**New Definitions and Terms**

- **Prior** — the probability distribution over parameter values before seeing the current data
- **Likelihood** — the probability of the observed data as a function of the parameter
- **Posterior** — the updated probability distribution over parameter values after observing the data
- **Evidence** — the normalizing constant in Bayes' rule; the overall probability of the observed data under the model

**Formulas**

$$
p(\theta \mid y) = \frac{p(y \mid \theta)\,p(\theta)}{p(y)}
$$

The posterior is proportional to likelihood times prior, with the evidence ensuring the result is a valid probability distribution.

```{python}
#| output: asis
print(slides.figure("Bayes rule is based in conditional probability"))
```

## 2.4 — Likelihood

This section introduces the coin-flip model as the main running example and defines the likelihood more concretely. The slides show both a graphical representation of the model and a mathematical one, then move from a single flip to the **Binomial** model for multiple flips. The key idea is that the likelihood tells us which parameter values make the observed data more or less plausible, and that multiplying the likelihood by the prior yields the posterior.

**New Definitions and Terms**

- **Binomial model** — a model for the number of successes in a fixed number of Bernoulli trials
- **Likelihood function** — the probability of the observed data viewed as a function of the unknown parameter

**Formulas**

$$
z \mid \theta, N \sim \operatorname{Binomial}(N, \theta)
$$

The number of heads $z$ in $N$ flips is modeled with a Binomial distribution whose parameter is the unknown coin probability $\theta$.

$$
p(z \mid \theta, N) = \binom{N}{z}\theta^z(1-\theta)^{N-z}
$$

This is the likelihood for the coin-flip example.

$$
p(\theta \mid z, N) \propto p(z \mid \theta, N)\,p(\theta)
$$

In grid calculation, the posterior is obtained point by point by multiplying prior and likelihood and then normalizing.

```{python}
#| output: asis
print(slides.figure("Likelihood for multiple coin flips"))
```

The likelihood has a strong influence on the posterior.

```{python}
#| output: asis
print(slides.figure("Changing likelihood affects posterior"))
```

## 2.5 — Grid calculation

This section shows how to compute a posterior directly on a dense grid of parameter values. The lecture's strategy is simple: evaluate the **prior** and the **likelihood** at many fixed values of $\theta$, multiply them point by point, and then normalize the resulting curve so that it becomes a proper probability distribution. The grid method is practical for one-parameter examples like the coin-flip model and gives a concrete way to see what Bayes' rule is doing computationally.

**New Definitions and Terms**

- **Grid calculation** — computing a posterior by evaluating it on a fixed grid of parameter values
- **Normalization** — rescaling a curve so that its total area is $1$

**Formulas**

$$
p(\theta \mid z, N) \propto p(z \mid \theta, N)\,p(\theta)
$$

On a grid, we compute this product at each sampled value of $\theta$.

$$
p(\theta \mid z, N) = \frac{p(z \mid \theta, N)\,p(\theta)}{\int p(z \mid \theta, N)\,p(\theta)\,d\theta}
$$

After taking the pointwise product, we normalize the curve so that it becomes a proper posterior density.

```{python}
#| output: asis
print(slides.figure("The grid method"))
```

## 2.6 — Prior

This section focuses on the prior as a probability distribution over parameter values before the current data are observed. The slides stress that a prior must be a proper probability distribution and that it expresses what values are considered possible or plausible under the model. They also show that the posterior is shaped jointly by the prior and the likelihood, so prior assumptions matter most when the data are limited.

**New Definitions and Terms**

- **Prior distribution** — a probability distribution representing uncertainty about a parameter before seeing the current dataset
- **Parameter uncertainty** — uncertainty about the true value of a model parameter

**Formulas**

$$
\int p(\theta)\,d\theta = 1
$$

A prior must integrate to $1$ because it is a probability distribution.

```{python}
#| output: asis
print(slides.figure("Posterior is affected by both priors and likelihood"))
```

## 2.7 — Beta distribution

This section introduces the **Beta distribution** as a flexible prior family for probabilities. Because it is defined on $[0,1]$, it matches the possible range of a coin-flip probability, and by changing its shape parameters it can represent uniform, biased, broad, or narrow prior beliefs. The lecture also introduces the **Beta function** as the normalizing constant and notes that the **Gamma function** extends the factorial to non-integer values.

**New Definitions and Terms**

- **Beta distribution** — a probability distribution on $[0,1]$ commonly used as a prior for unknown probabilities
- **Shape parameters** — parameters such as $\alpha$ and $\beta$ that determine the form of a distribution
- **Beta function** — the normalizing constant that makes the Beta density integrate to $1$
- **Gamma function** — a generalization of the factorial function

**Formulas**

$$
\theta \sim \operatorname{Beta}(\alpha, \beta)
$$

The Beta distribution is used to express prior uncertainty about the unknown probability $\theta$.

$$
p(\theta) = \frac{1}{B(\alpha,\beta)} \theta^{\alpha-1}(1-\theta)^{\beta-1}
$$

The Beta density is controlled by the shape parameters $\alpha$ and $\beta$.

```{python}
#| output: asis
print(slides.figure("What does the Beta distribution look like?"))
```

## 2.8 — Conjugate priors

This section shows that a Beta prior combined with a Binomial likelihood produces a Beta posterior. That analytic compatibility is what makes the Beta prior **conjugate** to the Binomial likelihood. The slides sketch the algebra, introduce the idea of simplifying Bayesian derivations with proportionality, and give the **pseudo-count** interpretation; the full algebraic derivation is available separately in the conjugate-prior derivation handout.

**New Definitions and Terms**

- **Conjugate prior** — a prior distribution that leads to a posterior in the same family after updating with the likelihood
- **Pseudo-count** — an interpretation of prior parameters as if they represented prior observations
- **Proportionality** — keeping only the terms that depend on the parameter and absorbing constants into the normalizing factor

**Formulas**

$$
\theta \sim \operatorname{Beta}(\alpha,\beta), \qquad z \mid \theta, N \sim \operatorname{Binomial}(N,\theta)
$$

This is the Beta-Binomial model discussed in the lecture.

$$
\theta \mid z, N \sim \operatorname{Beta}(\alpha + z,\; \beta + N - z)
$$

Observed heads add to $\alpha$ and observed tails add to $\beta$, producing an analytic posterior update.

```{python}
#| output: asis
print(slides.figure("Pseudo-count interpretation of conjugate prior"))
```

## 2.9 — Posterior distribution

This section applies the Beta-Binomial update repeatedly to the same coin-flip problem under several different priors. The main lesson is that the posterior remains a **distribution**, not just a point estimate, and that as more data arrive the posteriors become narrower and different priors tend to matter less. The lecture also emphasizes that for this model the final posterior depends on the total number of heads and tails, not on the order in which they arrived.

**Formulas**

$$
\theta \mid z, N \sim \operatorname{Beta}(\alpha + z,\; \beta + N - z)
$$

Repeated updating keeps the same form; only the sufficient counts change as more data accumulate.

```{python}
#| output: asis
print(slides.figure("Keep flipping coins"))
```

## 2.10 — Choosing priors

This section steps back from the coin example to ask how priors should be chosen in practice. The slides briefly review the history of so-called objective, maximum-entropy, vague, empirical, weakly informative, and automatic priors, then argue that prior choice should depend on the scientific problem and the strength of available background knowledge. The section ends with **prior elicitation**, where expert knowledge is translated into a prior distribution in an explicit, revisable way.

**New Definitions and Terms**

- **Weak prior** — a prior that places relatively broad constraints on plausible parameter values
- **Strong prior** — a prior that places substantial probability mass in a narrower set of values
- **Prior elicitation** — the process of translating domain knowledge into a prior distribution
- **Maximum entropy prior** — a prior chosen to satisfy stated constraints while adding as little extra structure as possible
- **Empirical prior** — a prior informed by external or previously collected data
- **Weakly informative prior** — a prior that regularizes an analysis without trying to dominate the data

```{python}
#| output: asis
print(slides.figure("Prior elicitation"))
```

## 2.11 — Preliz

This section introduces **Preliz** as a practical tool for exploring distributions and constructing priors from constraints. The lecture example asks for a Beta prior whose mass lies mostly between two bounds, and `maxent` is used to find a distribution that matches those constraints. Preliz is also presented as a broader reference for learning the shapes and uses of many probability distributions that will appear later in the course.

**New Definitions and Terms**

- **Preliz** — a Python package for exploring probability distributions and eliciting priors
- **maxent** — a Preliz function for finding a distribution that satisfies user-specified constraints

```{python}
#| output: asis
print(slides.figure("Preliz: a package for prior elicitation"))
```

## 2.12 — Next week

The lecture closes by explaining why **grid calculations** are useful for learning but do not scale well to models with many parameters. This motivates the move to **sampling** methods and to PyMC, which will allow the course to fit richer models without evaluating the posterior on an infeasibly large grid.

```{python}
#| output: asis
print(slides.figure("Sampling as an alternative to grid computation"))
```
