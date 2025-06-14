# Welcome to fasttransform


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Installation

Install latest from the GitHub
[repository](https://github.com/AnswerDotAI/fasttransform):

``` sh
$ pip install git+https://github.com/AnswerDotAI/fasttransform.git
```

or from [pypi](https://pypi.org/project/fasttransform/):

``` sh
$ pip install fasttransform
```

## Quick start

### Transform

Transform is a class that lets you create reusable data transformations.
You initialize a Transform by passing in or decorating a raw function.
The Transform then provides an enhanced version of that function via
`Transform.encodes`, which can be used in your data pipeline.

It provides various conveniences:

- **Reversibility**. You can collect the raw function and its inverse
  into one transform object.
- **Customized initialization** You can customize the exact behavior of
  a transform function on initialization.
- **Type-based mulitiple dispatch**. Transforms can specialize their
  behavior based on the runtime types of their arguments.
- **Type conversion/preservation**. Transforms help you maintain desired
  return types.

The simplest way to create a Transform is by decorating a function:

``` python
from fasttransform import Transform, Pipeline
```

``` python
@Transform
def add_one(x): 
    return x + 1

# Usage
add_one(2)
```

    3

### Reversibility

To make a transform reversible, you provide the raw function and its
inverse. This is useful in data pipelines where, for instance, you might
want to normalize and then de-normalize numerical values, or encode to
category indexes and then decode back to categories.

``` python
def enc(x): return x*2
def dec(x): return x//2

t = Transform(enc,dec)

t(2), t.decode(2), t.decode(t(2))
```

    (4, 1, 2)

### Customized initialization

You can customize an individual Transform instance at initialization
time, so that it can depend on aggregate properties of the data set.

Here we define a z-score normalization Transform by defining `encodes`
and `decodes` methods directly:

``` python
import statistics

class NormalizeMean(Transform):
    def setups(self, items): 
        self.mean = statistics.mean(items)
        self.std  = statistics.stdev(items)
    
    def encodes(self, x): 
        return (x - self.mean) / self.std
    
    def decodes(self, x): 
        return x * self.std + self.mean

normalize = NormalizeMean()
normalize.setup([1, 2, 3, 4, 5])
normalize.mean
```

    3

### Type-based multiple dispatch

Instead of providing one raw functions, you can provide multiple raw
functions which differ in their parameter types. Tranform will use
type-based dispatch to automatically execute the correct function.

This is handy when your inputs come in different types (eg., different
image formats, different numerical types).

``` python
def inc1(x:int): return x+1
def inc2(x:str): return x+"a"

t = Transform(enc=(inc1,inc2))

t(5), t('b')
```

    (6, 'ba')

If an input type does not match any of the type annotations then the
original input is returned.

``` python
add_one(2.0)
```

    3.0

``` python
normalize(3.0)
```

    0.0

### Type conversion/preservation

You initialize a Transform by passing in or decorating a raw function.

A Transform `encodes` or `decodes` will note the return type of its raw
function, which may be defined explicitly or implicitly, and enhance
type-handling behavior in three ways:

1.  **Guaranteed return type**. It will always return the return type of
    the raw function, promoting values if necessary.

2.  **Type Preservation**. It will return the runtime type of its
    argument, whenever that is a subtype of the return type.

3.  **Opt-out conversion**. If you explicitly mark the raw function’s
    return type as `None`, then it will not perform any type conversion
    or preservation.

Examples help make this clear:

#### Guaranteed return type

Say you define `FS`, a subclass of `float`. The usual Python type
promotion behavior means that an `FS` times a `float` is still a
`float`:

``` python
class FS(float):
  def __repr__(self): return f'FS({float(self)})'
 
f1 = float(1)
FS2 = FS(2)

val = f1 * FS2
type(val) # => float
```

    float

With Transform, you can define a new multiplication operation which will
be guaranteed to return a `FS`, because Transform reads the required raw
function’s annotated return type:

``` python
def double_FS(x)->FS: return FS(2)*x
t = Transform(double_FS)
val = t(1) 
assert isinstance(val,FS)
val
```

    FS(2.0)

#### Type preservation

Let us say that we define a transform *without* any return type
annotation, so that the raw function is defined only by the behavior of
multiplying its argument by the float 2.0.

Multiplying the subtype `FS` with the float value 2 would normally
return a `float`. However, Transform’s `encodes` will *preserve the
runtime type of its argument*, so that it returns `FS`:

``` python
def double(x): return x*2.0  # no type annotation
t = Transform(double)
fs1 = FS(1)
val = t(fs1)
assert isinstance(val,FS)
val # => FS(2), an FS value of 2
```

    FS(2.0)

#### Opt-out conversion

Sometimes you don’t want Transform to do any type-based logic. You can
opt-out of this system by declaring that your raw function’s return type
is `None`:

``` python
def double_none(x) -> None: return x*2.0  # "None" returnt type means "no conversion"
t = Transform(double_none)
fs1 = FS(1)
val = t(fs1)
assert isinstance(val,float)
val # => 2.0, a float of 2, because of fallback to standard Python type logic
```

    2.0

### Pipelines

Transforms can be combined into larger **Pipelines**:

``` python
def double(x): return x*2.0 
def halve(x): return x/2.0
dt = Transform(double,halve)

class NormalizeMean(Transform):
    def setups(self, items): 
        self.mean = statistics.mean(items)
        self.std  = statistics.stdev(items)
    
    def encodes(self, x):
        return (x - self.mean) / self.std
    
    def decodes(self, x):
        return x * self.std + self.mean


p = Pipeline((dt, normalize))

v = p(5)
v
```

    4.427188724235731

``` python
p.decode(v)
```

    5.0

### Documentation

This was just a quickstart. Learn more by reading the
[documentation](https://answerdotai.github.io/fasttransform/).
