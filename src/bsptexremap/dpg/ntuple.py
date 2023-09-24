# https://stackoverflow.com/a/76583710
from math import ceil,floor,trunc
from operator import (add,and_,eq,floordiv,ge,gt,invert,le,lshift,lt,mod,mul,ne,
  neg,or_,pos,rshift,sub,truediv,xor,)
from itertools import repeat
from typing import Iterable

class ntuple(tuple):
  def __lt__(a,b): return ntuple(map(lt,a,a._b(b)))
  def __le__(a,b): return ntuple(map(le,a,a._b(b)))
  def __eq__(a,b): return ntuple(map(eq,a,a._b(b)))
  def __ne__(a,b): return ntuple(map(ne,a,a._b(b)))
  def __gt__(a,b): return ntuple(map(gt,a,a._b(b)))
  def __ge__(a,b): return ntuple(map(ge,a,a._b(b)))
  def __add__(a,b): return ntuple(map(add,a,a._b(b)))
  def __sub__(a,b): return ntuple(map(sub,a,a._b(b)))
  def __mul__(a,b): return ntuple(map(mul,a,a._b(b)))
  def __matmul__(a,b): return sum(map(mul,a,a._b(b)))
  def __truediv__(a,b): return ntuple(map(truediv,a,a._b(b)))
  def __floordiv__(a,b): return ntuple(map(floordiv,a,a._b(b)))
  def __mod__(a,b): return ntuple(map(mod,a,a._b(b)))
  def __divmod__(a,b): return ntuple(map(divmod,a,a._b(b)))
  def __pow__(a,b,m=None): return ntuple(pow(a,b,m) for a,b in zip(a,a._b(b)))
  def __lshift__(a,b): return ntuple(map(lshift,a,a._b(b)))
  def __rshift__(a,b): return ntuple(map(rshift,a,a._b(b)))
  def __and__(a,b): return ntuple(map(and_,a,a._b(b)))
  def __xor__(a,b): return ntuple(map(xor,a,a._b(b)))
  def __or__(a,b): return ntuple(map(or_,a,a._b(b)))
  def __neg__(a): return ntuple(map(neg,a))
  def __pos__(a): return ntuple(map(pos,a))
  def __abs__(a): return ntuple(map(abs,a))
  def __invert__(a): return ntuple(map(invert,a))
  def __round__(a,n=None): return ntuple(round(e,n) for e in a)
  def __trunc__(a): return ntuple(map(trunc,a))
  def __floor__(a): return ntuple(map(floor,a))
  def __ceil__(a): return ntuple(map(ceil,a))
  def _b(a,b): return b if isinstance(b,Iterable) else repeat(b,len(a))