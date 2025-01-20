"""Definition of `Transform` and `Pipeline`"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_transform.ipynb.

# %% auto 0
__all__ = ['Sig', 'merge_funcs', 'Transform', 'InplaceTransform', 'DisplayedTransform', 'ItemTransform', 'get_func', 'Func']

# %% ../nbs/01_transform.ipynb 1
from typing import Any

from fastcore.imports import *
from fastcore.foundation import *
from fastcore.utils import *

from plum.function import Function
from plum import NotFoundLookupError

from .utils import get_name, is_tuple, retain_type

# %% ../nbs/01_transform.ipynb 9
def merge_funcs(*fs):
    "Merge multiple plum Functions by combining their methods"
    fs = fs[::-1]  # overwrite old implementations with new ones
    res = Function(fs[-1].methods[0].implementation)
    for f in fs: 
        for m in f.methods: res.dispatch(m.implementation)
    return res

# %% ../nbs/01_transform.ipynb 11
_tfm_methods = 'encodes','decodes','setups'
def _is_tfm_method(n, f): return n in _tfm_methods and callable(f)

# %% ../nbs/01_transform.ipynb 12
def _has_self_arg(f) -> bool:
    try: return f.__code__.co_varnames[0] == 'self'
    except (AttributeError, IndexError): return False

# %% ../nbs/01_transform.ipynb 13
def _get_self_type_annotation(f) -> type | None:
    "Get type annotation of 'self' if exists and is Transform subclass, else None"
    try: c = typing.get_type_hints(f)['self']
    except (TypeError, NameError, KeyError): return None
    if not issubclass(c,Transform) or c is Transform: raise ValueError("self must be subclass of Transform")
    return c
    

# %% ../nbs/01_transform.ipynb 14
class _TfmDict(dict):
    def __setitem__(self, k, v):
        if not _is_tfm_method(k, v): return super().__setitem__(k,v)
        if k not in self: super().__setitem__(k, Function(v))
        self[k].dispatch(v)

# %% ../nbs/01_transform.ipynb 15
class _TfmMeta(type):
    @classmethod
    def __prepare__(cls, name, bases): return _TfmDict()

    def __call__(cls, *args, **kwargs):
        if len(args)!=1 or len(kwargs)>0 or not _has_self_arg(args[0]): 
            return super().__call__(*args, **kwargs)
        f, nm = args[0], args[0].__name__
        c = _get_self_type_annotation(f) or cls
        if nm not in _tfm_methods: raise RuntimeError(f"{nm} not in {_tfm_methods}")         
        if not hasattr(c, nm): setattr(c, nm, Function(f).dispatch(f))
        else: getattr(c,nm).dispatch(f)
        return c


    def __new__(cls, name, bases, namespace):
        new_cls = super().__new__(cls, name, bases, namespace)
        for nm in _tfm_methods:
            if hasattr(new_cls, nm):
                funcs = [getattr(new_cls, nm)] + [getattr(b, nm,None) for b in bases]
                funcs = [f for f in funcs if f]
                if funcs: setattr(new_cls, nm, merge_funcs(*funcs))
        return new_cls

# %% ../nbs/01_transform.ipynb 16
class Transform(metaclass=_TfmMeta):
    "Delegates (`__call__`,`decode`,`setup`) to (<code>encodes</code>,<code>decodes</code>,<code>setups</code>) if `split_idx` matches"
    split_idx,init_enc,order,train_setup = None,None,0,None
    
    def __init__(self,enc=None,dec=None, split_idx=None, order=None):
        self.split_idx = ifnone(split_idx, self.split_idx)
        if order is not None: self.order=order 
        if enc:=L(enc): self.encodes = Function(enc[0])
        for e in enc: self.encodes.dispatch(e)
        if dec:=L(dec): self.decodes = Function(dec[0])
        for d in dec: self.decodes.dispatch(d)

    @property
    def name(self): return getattr(self, '_name', get_name(self))
    def __repr__(self):
        enc = len(self.encodes.methods) if hasattr(self, 'encodes') else 0
        dec = len(self.decodes.methods) if hasattr(self, 'decodes') else 0
        return f'{self.name}(enc:{enc},dec:{dec})'
    def __call__(self,*args,split_idx=None, **kwargs): return self._call('encodes', split_idx, *args,**kwargs)
    def decode(self, *args,split_idx=None, **kwargs): return self._call('decodes', split_idx, *args, **kwargs)
    def setup(self, items=None, train_setup=False):
        train_setup = train_setup if self.train_setup is None else self.train_setup
        setups = getattr(self,'setups',lambda o:o)
        return setups(getattr(items, 'train', items) if train_setup else items)

    def _call(self, nm, split_idx=None, *args, **kwargs):
        if split_idx!=self.split_idx and self.split_idx is not None: return args[0]
        if not hasattr(self, nm): return args[0]
        return self._do_call(nm, *args, **kwargs)

    def _do_call(self, nm, *args, **kwargs):
        if is_tuple(x:=args[0]): 
            res = tuple(self._do_call(nm, x_, *args[1:], **kwargs) for x_ in x)
            return retain_type(res, x, Any)
        f = getattr(self,nm)
        if isinstance(f,MethodType): f, f_args = f._f, (self,)+args
        else: f_args = args
        try: method, ret_type = f._resolve_method_with_cache(f_args)
        except NotFoundLookupError: return x
        return retain_type(method(*f_args,**kwargs), x, ret_type)


# %% ../nbs/01_transform.ipynb 150
class InplaceTransform(Transform):
    "A `Transform` that modifies in-place and just returns whatever it's passed"
    def _call(self, fn, split_idx=None, *args, **kwargs):
        super()._call(fn,split_idx,*args, **kwargs)
        return args[0]

# %% ../nbs/01_transform.ipynb 154
class DisplayedTransform(Transform):
    "A transform with a `__repr__` that shows its attrs"

    @property
    def name(self): return f"{super().name} -- {getattr(self,'__stored_args__',{})}\n"

# %% ../nbs/01_transform.ipynb 160
class ItemTransform(Transform):
    "A transform that always take tuples as items"
    _retain = True
    def __call__(self, x, **kwargs): return self._call1(x, '__call__', **kwargs)
    def decode(self, x, **kwargs):   return self._call1(x, 'decode', **kwargs)
    def _call1(self, x, name, **kwargs):
        if not is_tuple(x): return getattr(super(), name)(x, **kwargs)
        y = getattr(super(), name)(list(x), **kwargs)
        if not self._retain: return y
        if is_listy(y) and not isinstance(y, tuple): y = tuple(y)
        return retain_type(y, x, Any)
     

# %% ../nbs/01_transform.ipynb 169
def get_func(t, name, *args, **kwargs):
    "Get the `t.name` (potentially partial-ized with `args` and `kwargs`) or `noop` if not defined"
    f = nested_callable(t, name)
    return f if not (args or kwargs) else partial(f, *args, **kwargs)

# %% ../nbs/01_transform.ipynb 173
class Func():
    "Basic wrapper around a `name` with `args` and `kwargs` to call on a given type"
    def __init__(self, name, *args, **kwargs): self.name,self.args,self.kwargs = name,args,kwargs
    def __repr__(self): return f'sig: {self.name}({self.args}, {self.kwargs})'
    def _get(self, t): return get_func(t, self.name, *self.args, **self.kwargs)
    def __call__(self,t): return mapped(self._get, t)

# %% ../nbs/01_transform.ipynb 176
class _Sig():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return Func(k, *args, **kwargs)
        return _inner

Sig = _Sig()
     
