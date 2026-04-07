## Slide 1

### Statistics 367-1-4361 Models

Opher Donchin

## Slide 2

### 2.1 What is a statistical model

Estimation, models, and generative thinking

## Slide 3

### A statistical model is an idea of how data could be generated

- Data is generated stochastically (probabilistically):
- To describe that process, we need:
  - A particular distribution
  - Defined by specific parameters
Data analysis, 2022-2, Lecture 1
3 /  72

## Slide 4

### Very early, models of the world used in estimation

- Early researchers realized noisy data could be used for estimation
  - Laplace used Bayes’ rule (1812)
    - Estimate parameters of planetary orbits
    - Explicit mathematical model and inverse probability
Observations

## Slide 5

### In search for objectivity, estimation overshadowed modeling

- Stepping away from models
  - Models made sense for physical sciences
  - Racial “scientists” wanted to estimate abstract relations
    - Adolphe Quetelet (1835) estimated height of “average man”
    - Francis Galton (1869) : correlation of head size and intelligence
    - Karl Pearson (1890) : optimal estimates given noisy data
  - Frequentist statistics focuses on the behavior of “estimators”
    - An interest in “average man”
    - Something that can’t be modelled
      - A summary
      - Not a real physical process

## Slide 6

### Estimators as a goal of data analysis

Parameter

## Slide 7

### Models re-emerge in likelihood methods

- Stepping back towards models
  - Ronald Fisher
    - The Design of Experiments (1935)
      - Objectivity with political impact
    - Made likelihood central
    - Likelihood links parameter values to observed data
    - Models return as useful tools
Likelihood

## Slide 8

### Models are not just tools for estimation

- Harold Jeffreys
    - Theory of probability (1939)
    - Models express current scientific understanding
    - Data updates beliefs within the model
  - Working on internal structure of the earth from seismic waves
    - Parameters always have uncertainty
    - They are random variables

## Slide 9

### A model is an idea of how data is generated

- It has:
  - Probability distributions
  - Parameters
- 12 Angry Men:
  - Woman on train
    - Saw the boy stab his father
  - Man downstairs
    - Heard boy say “I’ll kill you”
    - Saw boy run down stairs
  - Weapon was switchblade
    - Like one owned by boy
  - Weak alibi

## Slide 10

### Evidence causes updating!

## Slide 11

### New evidence causes model updating

- Evidence accumulates:
  - Similar knife is easy to find
  - Etc.
- Jurors slowly become convinced
Time | Vote
0:06 | 11:1
0:28 | 10:2
0:46 | 9:3

## Slide 12

### 2.2 Conditional probability

Joint, marginal, and conditional probability

## Slide 13

### Joint probability is the probability of more than one variable

It can be used to find the conditional probability

## Slide 14

### Conditional probability can go either direction

It can be used to find the conditional probability

## Slide 15

### A relationship between c|r and r|c

## Slide 16

### Conditional probability can be applied to data and models

## Slide 17

### 2.3 Bayes rule

Prior, likelihood, posterior, and evidence

## Slide 18

### Bayes rule is based in conditional probability

## Slide 19

### We will use Baye’s rule to update our models

## Slide 20

### Baye’s rule can be counterintuitive

## Slide 21

### For us, each component has a name

## Slide 22

### 2.4 Likelihood

Binomial model, coin flip, and likelihood functions

## Slide 23

### Graphical representation of models can be helpful

Data
Likelihood
Prior

## Slide 24

### Models can be expressed mathematically

Data
Likelihood
Prior

## Slide 25

### The probability of getting z heads in N coin tosses

As a function of the parameter!

## Slide 26

### The likelihood function: Probability of data given the parameter

For multiple flips, the Binomial distribution

## Slide 27

### The binomial distribution

## Slide 28

### Likelihood for a simple coin flip

## Slide 29

### Likelihood for multiple coin flips

## Slide 30

### Bayes combines likelihood with prior

- Essentially:
  - Multiply prior by likelihood
  - To get posterior

## Slide 31

### Changing likelihood affects posterior

- As we add more data
  - Data will dominate prior
  - Except where prior is 0

## Slide 32

### 2.5 Grid calculation

Computing the posterior on a full grid

## Slide 33

### Grid calculation works point by point

## Slide 34

### The grid method

- “Sample” at fixed intervals
- Posterior is just prior times likelihood
- And these are both easy to calculate
- def posterior_from_product(theta, alpha, beta, z, n):
- product = beta_density(theta, alpha, beta) * binomial_likelihood(theta, z, n)
- return normalize_density(theta, product)
THETA_GRID = np.linspace(1e-4, 1 - 1e-4, 1200)
simple_posterior = posterior_from_curve(THETA_GRID, slide_prior, 1, 1)
slide_prior = triangular_prior_density(THETA_GRID)

## Slide 35

### Calculate first, then normalize

Normalizing is easy after you have the samples
- def normalize_density(theta, density):
- area = np.trapezoid(density, theta)
- return density / area
- def posterior_from_product(theta, alpha, beta, z, n):
- product = beta_density(theta, alpha, beta) * binomial_likelihood(theta, z, n)
- return normalize_density(theta, product)
THETA_GRID = np.linspace(1e-4, 1 - 1e-4, 1200)
simple_posterior = posterior_from_curve(THETA_GRID, slide_prior, 1, 1)
slide_prior = triangular_prior_density(THETA_GRID)

## Slide 36

### 2.6 Prior

Prior beliefs, parameter uncertainty, and model assumptions

## Slide 37

### The prior is a probability distribution

Must integrate to 1

## Slide 38

### Priors are ideas about what is possible

- We may be willing to accept any possibility
- Or be very opinionated

## Slide 39

### Posterior is affected by both priors and likelihood

## Slide 40

### 2.7 Beta distribution

Probability distributions, Beta priors, and shape parameters

## Slide 41

### Use the Beta distribution for a prior

The beta distribution:
The beta function:
The gamma function generalizes the factorial:

## Slide 42

### Use the Beta distribution for a prior

The beta distribution:
The beta function:
The beta function normalizes the beta distribution:

## Slide 43

### What does the Beta distribution look like?

- A large variety of “plausible” probabilities
  - Uniform
  - Biased
  - Narrow

## Slide 44

### Why use the beta distribution as a prior for the binomial likelihood

- Range of 0 to 1 makes sense for probility
- Flexibility to represent many possible priors
- The beta distribution is a conjugate prior for the binomial likelihood
- A conjugate prior for a likelihood:
- A family of priors where the posterior will also be in the family.

## Slide 45

### 2.8 Conjugate priors

Beta-binomial conjugacy and updating

## Slide 46

### Beta prior + Binomial posterior → Beta posterior

- This is a result of algebra
  - Briefly now in the slides
  - More fully in a handout
Prior:
Likelihood:
Posterior:

## Slide 47

### Beta is a conjugate prior for binomial likelihood

## Slide 48

### A simplified derivaiton

Posterior:
Prior:
Likelihood:

## Slide 49

Posterior:
Beta distribution

## Slide 50

### Bayesian simplification through proportionality

Posterior:
Prior:
Likelihood:
Beta distribution

## Slide 51

### Analytic solution to Bayesian estimation

- If the prior is a Beta distribution
  - Then the posterior is a different Beta distribution

## Slide 52

### Pseudo-count interpretation of conjugate prior

## Slide 53

### 2.9 Posterior distribution

Posterior updating and accumulation of evidence

## Slide 54

### Apply this to coin flipping

- Imagine three different priors
  - Uniform prior: a=1, b=1
  - Prior for unbiased: a=20, b=20
  - Positive skewed prior: a=1, b=4
Can you tell which is which?

## Slide 55

### Flip your first coin

- Imagine three different priors
- Flip a coin, get a head
- Update the posterior

## Slide 56

### Flip your second coin

- Imagine three different priors
- Flip two coins, get one head
- Update the posterior

## Slide 57

### Flip your third coin

- Imagine three different priors
- Flip three coins, get one head
- Update the posterior

## Slide 58

### Keep flipping coins

## Slide 59

### Still using grid method to find posterior

- for ax, n, z in zip(axes_flat[1:10], n_trials[1:], n_heads[1:]):
- ax.set_visible(True)
- for _, alpha, beta, color in PRIOR_SPECS:
- posterior = posterior_density(THETA_GRID, alpha, beta, z, n)
- ax.plot(THETA_GRID, posterior, color=color, linewidth=2.0)
- ax.axvline(theta_real, color="0.35", linestyle=":", linewidth=1.2)
- ax.set_title(f"N = {n}, z = {z}")
- format_theta_axis(ax, ylabel=None, xlabel=False)

## Slide 60

### Many things to learn from this figure

- A Bayesian analysis leads to a distribution
  - Mode of distribution gives most probable value
  - Spread of distribution gives uncertainty
- More data leads to:
  - Less spread, less uncertainty
  - Converging posteriors, agreement on most probable value
- Some priors are equivalent even with small amounts of data

## Slide 61

### One more thing to know

- We could add the data in different orders
  - The final result would be the same

## Slide 62

### 2.10 Choosing priors

Weak priors, strong priors, and prior elicitation

## Slide 63

### The history of choosing priors

- 1930s-1950s: Objective priors
  - Choose according to a mathematical principle
- 1960s: Maximum entropy priors
  - Minimize extra information given constraints
- 1980s-1990s: Vague priors
  - Make priors broad enough that they do not matter
  - An effort to appease frequentist critique
- 2000s: Empirical priors
  - Base priors on data
- 2010s: Weakly informative priors
  - Stabilize analyses
- 2020s: Automatic prior selection
  - Choose according to a mathematical principle

## Slide 64

### Choosing strong priors

- In many hard problems, strong priors make sense
  - Election polling
  - Weather prediction
  - Genetics
- Strong priors are necessary when there is weak data
- Strong priors are inappropriate when there is strong data
  - Unless you don’t trust the data
    - Like in election polling

## Slide 65

### Prior elicitation

- Approaches for translating expert knowledge into prior distributions
  - What questions does it make sense to ask an expert?
  - How can you take their answers and create a prior distribution?
  - How can you iterate this process to converge to a prior distribution that truly reflects the expert knowledge

## Slide 66

### 2.11 Preliz

Exploring distributions and finding priors

## Slide 67

### Preliz: a package for prior elicitation

- I’m pretty sure the coin’s probability is somewhere between 0.1 and 0.7
- maxent finds a Beta prior with X% of the probability between low and high
  - And displays it
- import preliz as pz
- dist = pz.Beta()
- pz.maxent(dist, 0.1, 0.7, 0.9)

## Slide 68

### Preliz is handy for learning distributions

- See the full gallery here:
  - https://preliz.readthedocs.io/en/latest/gallery_content.html
- We will use many of these distributions.
- This is a great reference
- And it can also help in prior selection

## Slide 69

### Preliz home page

https://preliz.readthedocs.io/en/latest/index.html

## Slide 70

### 2.12 Next week

Beyond grid calculations

## Slide 71

### Sampling as an alternative to grid computation

- Grid computation breaks down in high dimensions
- The better option:
  - More information where there is more probability
  - Sampling!

## Slide 72

### PyMC does sampling or us

Distributions
Samplers
Variational Bayes
Utilities
Models
Specialized applications
Arviz
Bambi
Preliz
PyMC
