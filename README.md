# What is Cosmap?

`cosmap` is an engine for asking big questions of big astronomical data. Questions like:

- How many galaxies should we expect to find in a randomly-selected patch of the sky, out to redshift 1.0?
- How does this number change as the patch of sky gets larger?
- What do their mass profiles look like?
- How does this mass profile evolve over cosmic time?

In short, if your analysis makes use of some large sky survey, like DES, HSC-SSP, or (soon enough) LSST, `cosmap` can help you worry less about managing data and more about designing and interpreting your next-generation analyses. 

`cosmap` is built on top of [`heinlein`](https://github.com/PatrickRWells/heinlein), which automates the management and retrieval of survey datasets in your computing environment. In short, if `heinlein` supports it, so does cosmap.