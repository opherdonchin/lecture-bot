```{python}
#| label: setup
import sys
from pathlib import Path

QMD_DIR = Path.cwd()
sys.path.append(str(QMD_DIR))

from slide_helpers import LectureSlides

slides = LectureSlides.from_config(
    "Lecture 1 Probabilities",
    qmd_dir=QMD_DIR,
    config_path=QMD_DIR / "handout_config.yml",
)
```

# Lecture Overview

Lecture 1 introduces the central problem of statistics: we want to understand real-world processes, but we only observe measurements. Statistics provides methods for reasoning from imperfect data to explanations of the processes that generated them. It establishes the essential cycle **reality → data → models → reality** and the relationshpi between data, models, and measurement. The lecture concludes by introducing probability distributions and the parameters used to describe them.

# Lecture Sections

## 1.1 — Why Statistics Exists

Statistics exists because we only observe **data produced by measurements**, not reality itself. Scientific reasoning therefore requires systematic methods for moving from imperfect observations back toward the underlying processes that generated them.

**New Definitions and Terms**

- **Statistics** — a set of methods for learning about the world using data

```{python}
#| output: asis
print(slides.figure("Why do we need statistics"))
```

## 1.2 — What Is Statistics

Statistics provides tools for connecting **reality, data, and models**, allowing us to use observations to reason about the processes that generated them. In biomedical engineering, data come from many sources such as physiological signals, behavioral measurements, imaging data, and experiments, and statistical models help organize these observations into explanations of biological systems.

**New Definitions and Terms**

- **Model** — a formal representation of a process that could generate the observed data

```{python}
#| output: asis
print(slides.figure("Reality, Data, and Models"))
```

## 1.3 — What Is Data

Data are the recorded results of **measurements**, and understanding how measurements are produced is essential for interpreting data correctly. Measurements convert real-world phenomena into recorded values, and data may also include quantities derived from those measurements. Because data must ultimately be stored and analyzed, they must be finite and representable.

**New Definitions and Terms**

- **Measurement** — the process of converting a real-world phenomenon into recorded values

Important measurement properties:

- **Precision** — consistency of repeated measurements
- **Validity** — whether the measurement reflects the intended quantity
- **Reliability** — stability of measurements across time or conditions

## 1.4 — Imperfect Data

All real data are imperfect because measurements are affected by noise, bias, and experimental conditions. These imperfections limit the conclusions that can be drawn from data and require careful interpretation. Researchers also have ethical responsibilities regarding how data are collected, analyzed, and communicated.

**New Definitions and Terms**

Types of data imperfection discussed in the lecture:

- **Sampling bias** — systematic distortion caused by which observations enter the dataset
- **Measurement error** — mismatch between the recorded value and the true quantity
- **Missing data** — absent observations that increase uncertainty and may introduce bias
- **Proxy measures** — indirect measurements used in place of the quantity of real interest
- **Data ethics** — principles governing responsible data collection, analysis, and interpretation

```{python}
#| output: asis
print(slides.figure("Missing data"))
```

## 1.5 — Types of Data

Different kinds of measurements produce different **types of data**, and recognizing the structure of the data is an essential step in choosing an appropriate statistical model. Scientific datasets often include continuous measurements as well as categorical or ordered variables, and many analyses combine several types of data simultaneously.

**New Definitions and Terms**

- **Continuous data** — numerical measurements on a continuous scale
- **Categorical data** — observations grouped into discrete categories
- **Ordinal data** — categorical values with a meaningful ordering

```{python}
#| output: asis
print(slides.figure("Combining different data types"))
```

## 1.6 — Probability and Uncertainty

Because data are imperfect, our conclusions about the world are uncertain. Probability provides a mathematical framework for representing and reasoning about this uncertainty. In scientific contexts, uncertainty arises either from inherent randomness in the world or from incomplete knowledge about a system. Probability distributions provide a way to represent these uncertainties quantitatively.

**New Definitions and Terms**

- **Probability** — a numerical representation of the likelihood of events
- **Probability distribution** — a function describing probabilities of possible outcomes
- **Aleatory uncertainty** — variability inherent in the system or process being studied
- **Epistemic uncertainty** — uncertainty due to incomplete knowledge about the system

**Formulas**

$$
P(A)
$$

Probability assigned to event $A$.

```{python}
#| output: asis
print(slides.figure("Two distinct ideas about probability"))
```

## 1.7 — Probability Distributions

A **probability distribution** describes how probability is assigned across the possible values of a random variable. Instead of asking whether a single event occurs, we describe the probability associated with *each possible outcome*.

Probability distributions are the main way we represent uncertainty in statistics. Different scientific processes produce different characteristic distributions, which describe how values are likely to be distributed.

Two broad classes of distributions are commonly used:

- **Discrete distributions** — probabilities assigned to distinct outcomes (for example, the number of successes in repeated trials)
- **Continuous distributions** — probability density spread across a continuous range of values

Distributions describe the **shape of uncertainty** in a variable. In the next section we will see how **parameters** describe the specific instance of a distribution for a particular dataset.

```{python}
#| output: asis
print(slides.figure("Random variables"))
```


## 1.8 — Parameters and Describing Distributions

Probability distributions can be summarized using numerical parameters that describe key properties such as their center, spread, and shape. Measures such as the mean or median describe central tendency, standard deviation and interquartile range describe spread, while other quantities describe other aspects of the distribution's shape such as asymmetry or tail behavior.

**New Definitions and Terms**

Measures of central tendency:

- **Mean** — the average value of a distribution
- **Median** — the central value that divides the distribution in half
- **Mode** — the point with the largest probability

Shape descriptors:

- **Skewness** — a measure of asymmetry in a distribution
- **Kurtosis** — a measure of tail weight and peak sharpness
- **Unimodal distribution** — a distribution with a single mode
- **Multimodal distribution** — a distribution with more than one mode

**Formulas**

Mean:

$$
\mu = \frac{1}{N} \sum_{i=1}^{N} x_i
$$

```{python}
#| output: asis
print(slides.figure("Measure of assymetry: Skewness"))
print('\n')
print(slides.figure("Sharpness of peak: Kurtosis"))
```

## 1.9 — About This Course

The course focuses on using probability and statistical models to analyze data and reason about uncertainty in biomedical engineering. Students will learn how to construct models, interpret data, and evaluate evidence using modern statistical tools.

```{python}
#| output: asis
print(slides.figure("Resources"))
```
