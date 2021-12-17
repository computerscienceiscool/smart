"""
Classes for parameters, species, compartments, reactions, fluxes, and forms
Model class contains functions to efficiently solve a system
"""
import pdb
import re
from collections import Counter
from collections import OrderedDict as odict
from collections import defaultdict as ddict
from typing import Type

import dolfin as d
import mpi4py.MPI as pyMPI
import pandas
import petsc4py.PETSc as PETSc
from termcolor import colored

Print = PETSc.Sys.Print

from copy import copy, deepcopy
from pprint import pprint

import numpy as np
import pint
import sympy
from scipy.integrate import cumtrapz, solve_ivp
from sympy import Heaviside, lambdify
from sympy.parsing.sympy_parser import parse_expr
from sympy.utilities.iterables import flatten
from tabulate import tabulate

import stubs
import stubs.common as common
from stubs import unit as ureg

color_print = common.color_print

import dataclasses
from dataclasses import dataclass

comm = d.MPI.comm_world
rank = comm.rank
size = comm.size
root = 0

# ====================================================
# ====================================================
# Base Classes
# ====================================================
# ====================================================
# class ObjectContainer:
#     """
#     Parent class containing general methods used by all "containers"
#     """
#     def __init__(self, ObjectClass, data):#df=None, Dict=None):
#         self.Dict = odict()
#         self.dtypes = {}
#         self.ObjectClass = ObjectClass
#         self.properties_to_print = [] # properties to print

#         # Load in data from either a stubs.model_building instance, dictionary, or pandas DataFrame
#         if isinstance(data, stubs.model_building.ObjectDF):
#             self.add_pandas_dataframe(data.df)
#         elif isinstance(data, dict):
#             self.Dict = odict(data)
#         elif isinstance(data, pandas.DataFrame):
#             self.add_pandas_dataframe(data)
#         else:
#             raise ValueError("Unknown data type.")

#     def add_property(self, property_name, item):
#         setattr(self, property_name, item)
#     def add_property_to_all(self, property_name, item):
#         for obj in self.values:
#             setattr(obj, property_name, item)
#     def add(self, item):
#         self[item.name] = item
#     def remove(self, name):
#         self.Dict.pop(name)
#     def add_pandas_dataframe(self, df):
#         # convert all the nans to nones
#         df = common.nan_to_none(df)
#         for _, row in df.iterrows():
#             itemDict = row.to_dict()
#             self[row.name] = self.ObjectClass(row.name, Dict=itemDict)
#         self.dtypes.update(df.dtypes.to_dict())
#     def get_property(self, property_name):
#         # returns a dict of properties
#         property_dict = {}
#         for key, obj in self.items:
#             property_dict[key] = getattr(obj, property_name)
#         return property_dict

#     @property
#     def size(self):
#         "Size of ObjectContainer"
#         return len(self.Dict)
#     @property
#     def items(self):
#         return self.Dict.items()
#     @property
#     def values(self):
#         return self.Dict.values()
#     @property
#     def keys(self):
#         return self.Dict.keys()

#     def __getitem__(self, key):
#         "syntactic sugar to allow: objcontainer[key] = objcontainer[key]"
#         return self.Dict[key]
#     def __setitem__(self, key, newvalue):
#         "syntactic sugar to allow: objcontainer[key] = objcontainer[key]"
#         self.Dict[key] = newvalue

#     def where_equals(self, property_name, value):
#         """
#         Links objects from ObjectContainer2 to ObjectContainer1 (the ObjectContainer invoking
#         this method).

#         Parameters
#         ----------
#         property_name : str
#             Name of property to check values of
#         value : variable type
#             Value to check against

#         Example Usage
#         -------------
#         cc.where_equals('compartment_name', 'cyto')

#         Returns
#         -------
#         objectList: list
#             List of objects from ObjectContainer that matches the criterion
#         """
#         objList = []
#         for key, obj in self.items:
#             if getattr(obj, property_name) == value:
#                 objList.append(obj)
#         return objList

#     def _link_object(self, ObjectContainer2, property_name1, property_name2, linked_name, value_is_key=False):
#         """
#         Links objects from ObjectContainer2 to ObjectContainer1 (the ObjectContainer invoking
#         this method).

#         Parameters
#         ----------
#         with_attribution : bool, Optional, default: True
#             Set whether or not to display who the quote is from
#         ObjectContainer2 : ObjectContainer type
#             ObjectContainer with objects we are linking to
#         property_name1 : str
#             Name of property of object in ObjectContainer1 to match
#         property_name2 : str
#             Name of property of object in ObjectContainer2 to match
#         linked_name : str
#             Name of new property in ObjectContainer1 with linked object

#         Example Usage
#         -------------
#         sc = {'key0': sd0, 'key1': sd1}; cc = {'key0': cd0, 'key1': cd1}
#         sd0.compartment_name == 'cyto'
#         cd0.name == 'cyto'
#         >> sc._link_object(cc,'compartment_name','name','compartment')
#         sd0.compartment == cd0

#         Returns
#         -------
#         ObjectContainer1 : ObjectContainer
#             ObjectContainer where each object has an added property linking to some
#             object from ObjectContainer2
#         """
#         for _, obj1 in self.items:
#             obj1_value = getattr(obj1, property_name1)
#             # if type dict, then match values of entries with ObjectContainer2
#             if isinstance(obj1_value, dict):
#                 newDict = odict()
#                 for key, value in obj1_value.items():
#                     objList = ObjectContainer2.where_equals(property_name2, value)
#                     if len(objList) != 1:
#                         raise Exception("Property %s with value %s does not match %s (either none or more than one objects match)"
#                                         % (property_name2, value, objList))
#                     if value_is_key:
#                         newDict.update({value: objList[0]})
#                     else:
#                         newDict.update({key: objList[0]})

#                 setattr(obj1, linked_name, newDict)
#             #elif type(obj1_value) == list or type(obj1_value) == set:
#             #    newList = []
#             #    for value in obj1_value:
#             #        objList = ObjectContainer2.where_equals(property_name2, value)
#             #        if len(objList) != 1:
#             #            raise Exception('Either none or more than one objects match this condition')
#             #        newList.append(objList[0])
#             #    setattr(obj1, linked_name, newList)
#             elif type(obj1_value) == list or type(obj1_value) == set:
#                 newDict = odict()
#                 for value in obj1_value:
#                     objList = ObjectContainer2.where_equals(property_name2, value)
#                     if len(objList) != 1:
#                         raise Exception("Property %s with value %s does not match %s (either none or more than one objects match)"
#                                         % (property_name2, value, objList))
#                     newDict.update({value: objList[0]})
#                 setattr(obj1, linked_name, newDict)
#             # standard behavior
#             else:
#                 objList = ObjectContainer2.where_equals(property_name2, obj1_value)
#                 if len(objList) != 1:
#                     raise Exception("Property %s with value %s does not match %s (either none or more than one objects match)"
#                                     % (property_name2, obj1_value, objList))
#                 setattr(obj1, linked_name, objList[0])

#     def _copy_linked_property(self, linked_name, linked_name_property, property_name):
#         """
#         Convenience function to copy a property from a linked object
#         """
#         for _, obj in self.items:
#             linked_obj = getattr(obj, linked_name)
#             setattr(obj, property_name, getattr(linked_obj, linked_name_property))


#     def do_to_all(self, method_name, kwargs=None):
#         for name, instance in self.items:
#             if kwargs is None:
#                 getattr(instance, method_name)()
#             else:
#                 getattr(instance, method_name)(**kwargs)
    
#     def get_pandas_dataframe(self, properties_to_print=[], include_idx=True):
#         df = pandas.DataFrame()
#         if include_idx:
#             if properties_to_print and 'idx' not in properties_to_print:
#                 properties_to_print.insert(0, 'idx')
#             for idx, (name, instance) in enumerate(self.items):
#                 df = df.append(instance.get_pandas_series(properties_to_print=properties_to_print, idx=idx))
#         else:
#             for idx, (name, instance) in enumerate(self.items):
#                 df = df.append(instance.get_pandas_series(properties_to_print=properties_to_print))
#         # sometimes types are recast. change entries into their original types
#         for dtypeName, dtype in self.dtypes.items():
#             if dtypeName in df.columns:
#                 df = df.astype({dtypeName: dtype})

#         return df

#     def print_to_latex(self, properties_to_print=[], escape=False,
#                        include_idx=False):
#         df = self.get_pandas_dataframe(properties_to_print=properties_to_print,
#                                        include_idx=include_idx)

#         # converts Pint units to latex format
#         unit_to_tex = lambda unit: '${:L}$'.format(unit._units)
#         name_to_tex = lambda name: '$' + name.replace('_', '\_') + '$'
#         # bit of a hack... check the first row to guess which columns contain
#         # either Pint unit or quantity objects so we may convert them
#         for name, value in list(df.iloc[0].iteritems()):
#             if hasattr(value, '_units'):
#                 df[name] = df[name].apply(unit_to_tex)
#             if name == 'name':
#                 df[name] = df[name].apply(name_to_tex)
#             if name == 'idx' and include_idx == False:
#                 df = df.drop('idx',axis=1)

#         with pandas.option_context("max_colwidth", 1000):
#             tex_str = df.to_latex(index=False, longtable=True, escape=escape)
#             print(tex_str)

#     def get_index(self, idx):
#         """
#         Get an element of the object container ordered dict by referencing its index
#         """
#         return list(self.values)[idx]

#     def print(self, tablefmt='fancy_grid', properties_to_print=[]):
#         if rank == root:
#             if properties_to_print:
#                 if type(properties_to_print) != list: properties_to_print=[properties_to_print]
#             elif hasattr(self, 'properties_to_print'):
#                 properties_to_print = self.properties_to_print
#             df = self.get_pandas_dataframe(properties_to_print=properties_to_print)
#             if properties_to_print:
#                 df = df[properties_to_print]

#             print(tabulate(df, headers='keys', tablefmt=tablefmt))#,
#                    #headers='keys', tablefmt=tablefmt), width=120)
#         else:
#             pass

#     def __str__(self):
#         df = self.get_pandas_dataframe(properties_to_print=self.properties_to_print)
#         df = df[self.properties_to_print]

#         return tabulate(df, headers='keys', tablefmt='fancy_grid')

#     def vprint(self, keyList=None, properties_to_print=[], print_all=False):
#         # in order of priority: kwarg, container object property, else print all keys
#         if rank == root:
#             if keyList:
#                 if type(keyList) != list: keyList=[keyList]
#             elif hasattr(self, 'keyList'):
#                 keyList = self.keyList
#             else:
#                 keyList = list(self.keys)

#             if properties_to_print:
#                 if type(properties_to_print) != list: properties_to_print=[properties_to_print]
#             elif hasattr(self, 'properties_to_print'):
#                 properties_to_print = self.properties_to_print

#             if print_all: properties_to_print = []
#             for key in keyList:
#                 self[key].print(properties_to_print=properties_to_print)
#         else:
#             pass


# class ObjectInstance:
#     """
#     Parent class containing general methods used by all stubs
#     "objects": i.e. parameters, species, compartments, reactions, fluxes, forms
#     """
#     def __init__(self, name, Dict=None):
#         self.name = name
#         if Dict:
#             self.fromDict(Dict)
#     def fromDict(self, Dict):
#         for key, item in Dict.items():
#             setattr(self, key, item)
#     def combineDicts(self, dict1=None, dict2=None, new_dict_name=None):
#         setattr(self, new_dict_name, getattr(self,dict1).update(getattr(self,dict2)))
#     def assemble_units(self, value_name=None, unit_name='unit', assembled_name=None):
#         """
#         Simply multiplies a value by a unit (pint type) to create a pint "Quantity" object
#         """
#         if not assembled_name:
#             assembled_name = unit_name

#         value = 1 if not value_name else getattr(self, value_name)
#         #value = getattr(self, value_name)
#         unit = getattr(self, unit_name)
#         if type(unit) == str:
#             unit = ureg(unit)
#         setattr(self, assembled_name, value*unit)

#     def get_pandas_series(self, properties_to_print=[], idx=None):
#         if properties_to_print:
#             dict_to_convert = odict({'idx': idx})
#             dict_to_convert.update(odict([(key,val) for (key,val) in self.__dict__.items() if key in properties_to_print]))
#         else:
#             dict_to_convert = self.__dict__
#         return pandas.Series(dict_to_convert, name=self.name)
#     def print(self, properties_to_print=[]):
#         if rank==root:
#             print("Name: " + self.name)
#             # if a custom list of properties to print is provided, only use those
#             if properties_to_print:
#                 dict_to_print = dict([(key,val) for (key,val) in self.__dict__.items() if key in properties_to_print])
#             else:
#                 dict_to_print = self.__dict__
#             pprint(dict_to_print, width=240)
#         else:
#             pass

class ObjectContainer:
    """
    Parent class containing general methods used by all "containers"
    """
    def __init__(self, ObjectClass):#df=None, Dict=None):
        self.Dict = odict()
        self._ObjectClass = ObjectClass
        self.properties_to_print = [] # properties to print

        # ways to add in data: list, 

        # if data is not None:
        #     # Load in data from either a stubs.model_building instance, dictionary, or pandas DataFrame
        #     # if isinstance(data, stubs.model_building.ObjectDF):
        #     #     self.add_pandas_dataframe(data.df)
        #     if isinstance(data, dict):
        #         self.Dict = odict(data)
        #     # elif isinstance(data, pandas.DataFrame):
        #     #     self.add_pandas_dataframe(data)
        #     else:
        #         raise ValueError("Unknown data type.")

    # ==============================================================================
    # ObjectContainer - General methods
    # ------------------------------------------------------------------------------
    # General properties/methods to emulate some dictionary-like structure
    # + add some misc useful structure
    # ==============================================================================
    @property
    def size(self):
        "Size of ObjectContainer"
        return len(self.Dict)
    @property
    def items(self):
        return self.Dict.items()
    @property
    def values(self):
        return self.Dict.values()
    @property
    def keys(self):
        return self.Dict.keys()
    @property
    def indices(self):
        return enumerate(self.keys)

    def __getitem__(self, key):
        "syntactic sugar to allow: objcontainer[key] = objcontainer[key]"
        return self.Dict[key]
    def __setitem__(self, key, newvalue):
        "syntactic sugar to allow: objcontainer[key] = objcontainer[key]"
        self.Dict[key] = newvalue

    def add(self, *data):
        # Adding in the ObjectInstance directly
        if len(data) == 1 and isinstance(data, self._ObjectClass):
            self[data.name] = data
        # Adding in an iterable of ObjectInstances
        elif len(data) == 1:
            # check if input is an iterable and if so add it item by item
            try:
                iterator = iter(data[0])
            except:
                raise TypeError("Data being added to ObjectContainer must be either the ObjectClass or an iterator.")
            else:
                data=data[0]
                if all([isinstance(obj, self._ObjectClass) for obj in data]):
                    for obj in data:
                        self[obj.name] = obj
        # Adding via ObjectInstance arguments 
        else:
            obj = self._ObjectClass(*data)
            self[obj.name] = obj


    def remove(self, name):
        if type(name) != str:
            raise TypeError("Argument must be the name of an object [str] to remove.")
        self.Dict.pop(name)
    def add_property_to_all(self, property_name, item):
        for obj in self.values:
            setattr(obj, property_name, item)
    def get_property(self, property_name):
        # returns a dict of properties
        property_dict = {}
        for key, obj in self.items:
            property_dict[key] = getattr(obj, property_name)
        return property_dict
    def get_index(self, idx):
        """
        Get an element of the object container ordered dict by referencing its index
        """
        return list(self.values)[idx]
    def do_to_all(self, method_name, kwargs=None):
        for name, instance in self.items:
            if kwargs is None:
                getattr(instance, method_name)()
            else:
                getattr(instance, method_name)(**kwargs)

    # ==============================================================================
    # ObjectContainer - Internal methods
    # ------------------------------------------------------------------------------
    # Mostly methods called by Model.initialize()
    # ==============================================================================

    # ==============================================================================
    # ObjectContainer - Printing/data-formatting related methods
    # ==============================================================================   
    def get_pandas_dataframe(self, properties_to_print=[], include_idx=True):
        df = pandas.DataFrame()
        if include_idx:
            if properties_to_print and 'idx' not in properties_to_print:
                properties_to_print.insert(0, 'idx')
            for idx, (name, instance) in enumerate(self.items):
                df = df.append(instance.get_pandas_series(properties_to_print=properties_to_print, idx=idx))
        else:
            for idx, (name, instance) in enumerate(self.items):
                df = df.append(instance.get_pandas_series(properties_to_print=properties_to_print))
        # # sometimes types are recast. change entries into their original types
        # for dtypeName, dtype in self.dtypes.items():
        #     if dtypeName in df.columns:
        #         df = df.astype({dtypeName: dtype})

        return df

    def print_to_latex(self, properties_to_print=[], escape=False,
                       include_idx=False):
        df = self.get_pandas_dataframe(properties_to_print=properties_to_print,
                                       include_idx=include_idx)

        # converts Pint units to latex format
        unit_to_tex = lambda unit: '${:L}$'.format(unit._units)
        name_to_tex = lambda name: '$' + name.replace('_', '\_') + '$'
        # bit of a hack... check the first row to guess which columns contain
        # either Pint unit or quantity objects so we may convert them
        for name, value in list(df.iloc[0].iteritems()):
            if hasattr(value, '_units'):
                df[name] = df[name].apply(unit_to_tex)
            if name == 'name':
                df[name] = df[name].apply(name_to_tex)
            if name == 'idx' and include_idx == False:
                df = df.drop('idx',axis=1)

        with pandas.option_context("max_colwidth", 1000):
            tex_str = df.to_latex(index=False, longtable=True, escape=escape)
            print(tex_str)

    def print(self, tablefmt='fancy_grid', properties_to_print=[]):
        if rank == root:
            if properties_to_print:
                if type(properties_to_print) != list: properties_to_print=[properties_to_print]
            elif hasattr(self, 'properties_to_print'):
                properties_to_print = self.properties_to_print
            df = self.get_pandas_dataframe(properties_to_print=properties_to_print)
            if properties_to_print:
                df = df[properties_to_print]

            print(tabulate(df, headers='keys', tablefmt=tablefmt))#,
                   #headers='keys', tablefmt=tablefmt), width=120)
        else:
            pass

    def __str__(self):
        df = self.get_pandas_dataframe(properties_to_print=self.properties_to_print)
        df = df[self.properties_to_print]

        return tabulate(df, headers='keys', tablefmt='fancy_grid')

    def vprint(self, keyList=None, properties_to_print=[], print_all=False):
        # in order of priority: kwarg, container object property, else print all keys
        if rank == root:
            if keyList:
                if type(keyList) != list: keyList=[keyList]
            elif hasattr(self, 'keyList'):
                keyList = self.keyList
            else:
                keyList = list(self.keys)

            if properties_to_print:
                if type(properties_to_print) != list: properties_to_print=[properties_to_print]
            elif hasattr(self, 'properties_to_print'):
                properties_to_print = self.properties_to_print

            if print_all: properties_to_print = []
            for key in keyList:
                self[key].print(properties_to_print=properties_to_print)
        else:
            pass


class ObjectInstance:
    """
    Parent class containing general methods used by all stubs
    "objects": i.e. parameters, species, compartments, reactions, fluxes, forms
    """
    #def __init__(self):
    # if Dict:
    #     self.fromDict(Dict)
    # ==============================================================================
    # ObjectInstance - 
    # ============================================================================== 
    # def fromDict(self, Dict):
    #     for key, item in Dict.items():
    #         setattr(self, key, item)
    def _convert_pint_quantity_to_unit(self):
        # strip the magnitude and keep the units. Warn if magnitude!=1
        for name, attr in vars(self).items():
            if isinstance(attr, pint.Quantity):
                setattr(self, name, common.pint_quantity_to_unit(attr))
        
    def _check_input_type_validity(self):
        "Check that the inputs have the same type (or are convertible) to the type hint."
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                try:
                    setattr(self, field.name, field.type(value))
                except:
                    raise TypeError(f"Object \"{self.name}\" type error: the attribute \"{field.name}\" is expected to be {field.type}, got {type(value)} instead. "
                                    f"Conversion to the expected type was attempted but unsuccessful.")
    def _convert_pint_unit_to_quantity(self):
        # convert pint units to quantity
        for name, attr in vars(self).items():
            if isinstance(attr, pint.Unit):
                setattr(self, name, common.pint_unit_to_quantity(attr))

    def get_pandas_series(self, properties_to_print=[], idx=None):
        if properties_to_print:
            dict_to_convert = odict({'idx': idx})
            dict_to_convert.update(odict([(key,val) for (key,val) in self.__dict__.items() if key in properties_to_print]))
        else:
            dict_to_convert = self.__dict__
        return pandas.Series(dict_to_convert, name=self.name)
    def print(self, properties_to_print=[]):
        if rank==root:
            print("Name: " + self.name)
            # if a custom list of properties to print is provided, only use those
            if properties_to_print:
                dict_to_print = dict([(key,val) for (key,val) in self.__dict__.items() if key in properties_to_print])
            else:
                dict_to_print = self.__dict__
            pprint(dict_to_print, width=240)
        else:
            pass


# ==============================================================================
# ==============================================================================
# Classes for parameters, species, compartments, reactions, and fluxes
# ==============================================================================
# ==============================================================================

class ParameterContainer(ObjectContainer):
    def __init__(self):
        super().__init__(Parameter)

        self.properties_to_print = ['name', 'value', 'unit', 'is_time_dependent', 'sym_expr', 'notes', 'group']

@dataclass
class Parameter(ObjectInstance):
    name: str
    value: float
    unit: pint.Unit
    notes: str=''
    is_time_dependent: bool=False
    group: str=''
    sampling_file: str=''
    sym_expr: str=''
    preintegrated_sym_expr: str=''

    def __post_init__(self):
        self._convert_pint_quantity_to_unit()
        self._check_input_type_validity()
        self._convert_pint_unit_to_quantity()
        self.check_validity()

        self.value_unit = self.value*self.unit
        self._assemble_time_dependent_parameters()

    def check_validity(self):
        if self.is_time_dependent:
            if all([x=='' for x in [self.sampling_file, self.sym_expr, self.preintegrated_sym_expr]]):
                raise ValueError(f"Parameter {self.name} is marked as time dependent but is not defined in terms of time.")

    def _assemble_time_dependent_parameters(self):
        if not self.is_time_dependent:
            return
        # Parse the given string to create a sympy expression
        if self.sym_expr:
            self.sym_expr = parse_expr(self.sym_expr)
            Print("Creating dolfin object for time-dependent parameter %s" % self.name)
            self.dolfinConstant = d.Constant(self.value)
        if self.preintegrated_sym_expr:
            self.preintegrated_sym_expr = parse_expr(self.preintegrated_sym_expr)
        # load in sampling data file
        if self.sampling_file:
            self.sampling_data = np.genfromtxt(self.sampling_file, dtype='float',
                                               delimiter=',')
            Print("Creating dolfin object for time-dependent parameter %s" % self.name)
            self.dolfinConstant = d.Constant(self.value)

            # preintegrate sampling data
            int_data = cumtrapz(self.sampling_data[:,1], x=self.sampling_data[:,0], initial=0)
            # concatenate time vector
            self.preint_sampling_data = common.np_smart_hstack(self.sampling_data[:,0], int_data)



class SpeciesContainer(ObjectContainer):
    def __init__(self):
        super().__init__(Species)

        self.properties_to_print = ['name', 'compartment_name', 'compartment_index', 'concentration_units', 'D', 'initial_condition', 'group']

    def assemble_compartment_indices(self, rc, cc):
        """
        Adds a column to the species dataframe which indicates the index of a species relative to its compartment
        """
        num_species_per_compartment = rc.get_species_compartment_counts(self, cc)
        for compartment, num_species in num_species_per_compartment.items():
            idx = 0
            comp_species = [sp for sp in self.values if sp.compartment_name==compartment]
            for sp in comp_species:
                if sp.is_in_a_reaction:
                    sp.compartment_index = idx
                    idx += 1
                else:
                    print('Warning: species %s is not used in any reactions!' % sp.name)

    def assemble_dolfin_functions(self, rc, cc):
        """
        define dof/solution vectors (dolfin trialfunction, testfunction, and function types) based on number of species appearing in reactions
        IMPORTANT: this function will create additional species on boundaries in order to use operator-splitting later on
        e.g.
        A [cyto] + B [pm] <-> C [pm]
        Since the value of A is needed on the pm there will be a species A_b_pm which is just the values of A on the boundary pm
        """

        # functions to run beforehand as we need their results
        num_species_per_compartment = rc.get_species_compartment_counts(self, cc)
        #cc.get_min_max_dim() # refactor
        self.assemble_compartment_indices(rc, cc)
        cc.add_property_to_all('is_in_a_reaction', False)
        cc.add_property_to_all('V', None)

        V, u, v = {}, {}, {}
        for compartment_name, num_species in num_species_per_compartment.items():
            compartmentDim = cc[compartment_name].dimensionality
            cc[compartment_name].num_species = num_species
            if rank==root:
                print('Compartment %s (dimension: %d) has %d species associated with it' %
                      (compartment_name, compartmentDim, num_species))

            # u is the actual function. t is for linearized versions. k is for picard iterations. n is for last time-step solution
            if num_species == 1:
                V[compartment_name] = d.FunctionSpace(cc.meshes[compartment_name], 'P', 1)
                u[compartment_name] = {'u': d.Function(V[compartment_name], name="concentration_u"), 't': d.TrialFunction(V[compartment_name]),
                'k': d.Function(V[compartment_name]), 'n': d.Function(V[compartment_name])}
                v[compartment_name] = d.TestFunction(V[compartment_name])
            else: # vector space
                V[compartment_name] = d.VectorFunctionSpace(cc.meshes[compartment_name], 'P', 1, dim=num_species)
                u[compartment_name] = {'u': d.Function(V[compartment_name], name="concentration_u"), 't': d.TrialFunctions(V[compartment_name]),
                'k': d.Function(V[compartment_name]), 'n': d.Function(V[compartment_name])}
                v[compartment_name] = d.TestFunctions(V[compartment_name])

        # now we create boundary functions, i.e. interpolations of functions defined on the volume
        # to function spaces of the surrounding mesh
        V['boundary'] = {}
        for compartment_name, num_species in num_species_per_compartment.items():
            compartmentDim = cc[compartment_name].dimensionality
            if compartmentDim == cc.max_dim: # mesh may have boundaries
                V['boundary'][compartment_name] = {}
                for mesh_name, mesh in cc.meshes.items():
                    if compartment_name != mesh_name and mesh.topology().dim() < compartmentDim:
                        if num_species == 1:
                            boundaryV = d.FunctionSpace(mesh, 'P', 1)
                        else:
                            boundaryV = d.VectorFunctionSpace(mesh, 'P', 1, dim=num_species)
                        V['boundary'][compartment_name].update({mesh_name: boundaryV})
                        u[compartment_name]['b_'+mesh_name] = d.Function(boundaryV, name="concentration_ub")

        # now we create volume functions, i.e. interpolations of functions defined on the surface
        # to function spaces of the associated volume
        V['volume'] = {}
        for compartment_name, num_species in num_species_per_compartment.items():
            compartmentDim = cc[compartment_name].dimensionality
            if compartmentDim == cc.min_dim: # mesh may be a boundary with a connected volume
                V['volume'][compartment_name] = {}
                for mesh_name, mesh in cc.meshes.items():
                    if compartment_name != mesh_name and mesh.topology().dim() > compartmentDim:
                        if num_species == 1:
                            volumeV = d.FunctionSpace(mesh, 'P', 1)
                        else:
                            volumeV = d.VectorFunctionSpace(mesh, 'P', 1, dim=num_species)
                        V['volume'][compartment_name].update({mesh_name: volumeV})
                        u[compartment_name]['v_'+mesh_name] = d.Function(volumeV, name="concentration_uv")

        # associate indexed functions with dataframe
        for key, sp in self.items:
            sp.u = {}
            sp.v = None
            if sp.is_in_a_reaction:
                sp.compartment.is_in_a_reaction = True
                num_species = sp.compartment.num_species
                for key in u[sp.compartment_name].keys():
                    if num_species == 1:
                        sp.u.update({key: u[sp.compartment_name][key]})
                        sp.v = v[sp.compartment_name]
                    else:
                        sp.u.update({key: u[sp.compartment_name][key][sp.compartment_index]})
                        sp.v = v[sp.compartment_name][sp.compartment_index]

        # # associate function spaces with dataframe
        for key, comp in cc.items:
            if comp.is_in_a_reaction:
                comp.V = V[comp.name]

        self.u = u
        self.v = v
        self.V = V

@dataclass
class Species(ObjectInstance):
    name: str
    initial_condition: float
    concentration_units: pint.Unit
    D: float
    D_units: pint.Unit
    compartment_name: str
    group: str=''

    def __post_init__(self):
        self.sub_species = {} # additional compartments this species may live in in addition to its primary one
        self.is_in_a_reaction = False
        self.is_an_added_species = False
        self.dof_map = {}

        self._convert_pint_quantity_to_unit()
        self._check_input_type_validity()
        self._convert_pint_unit_to_quantity()
        self.check_validity()

    def check_validity(self):
        # checking values
        if self.initial_condition < 0.0:
            raise ValueError(f"Initial condition for species {self.name} must be greater or equal to 0.")
        if self.D < 0.0:
            raise ValueError(f"Diffusion coefficient for species {self.name} must be greater or equal to 0.")
        # checking units
        if not self.D_units.check('[length]^2/[time]'):
            raise ValueError(f"Units of diffusion coefficient for species {self.name} must be dimensionally equivalent to [length]^2/[time].")
        if not any([self.concentration_units.check(f'mole/[length]^{dim}') for dim in [1,2,3]]):
            raise ValueError(f"Units of concentration for species {self.name} must be dimensionally equivalent to mole/[length]^dim where dim is either 1, 2, or 3.")

# class Species(ObjectInstance):
#     def __init__(self, name, Dict=None):
#         super().__init__(name, Dict)
#         self.sub_species = {} # additional compartments this species may live in in addition to its primary one
#         self.is_in_a_reaction = False
#         self.is_an_added_species = False
#         self.dof_map = {}

class CompartmentContainer(ObjectContainer):
    def __init__(self):
        super().__init__(Compartment)

        self.properties_to_print = ['name', 'dimensionality', 'num_species', 'num_vertices', 'cell_marker', 'is_in_a_reaction', 'nvolume']
        self.meshes = {}
        self.vertex_mappings = {} # from submesh -> parent indices
#    def load_mesh(self, mesh_key, mesh_str):
#        self.meshes[mesh_key] = d.Mesh(mesh_str)
#
    def extract_submeshes(self, main_mesh_str='main_mesh', save_to_file=False):
        main_mesh  = self[main_mesh_str]
        surface_dim = main_mesh.dimensionality - 1

        self[main_mesh_str].mesh = self.meshes[main_mesh_str]

        vmesh = self.meshes[main_mesh_str]
        bmesh = d.BoundaryMesh(vmesh, "exterior")

        # Very odd behavior - when bmesh.entity_map() is called together with .array() it will return garbage values. We
        # should only call entity_map once to avoid this
        temp_emap_0  = bmesh.entity_map(0)
        bmesh_emap_0 = deepcopy(temp_emap_0.array())
        temp_emap_n  = bmesh.entity_map(surface_dim)
        bmesh_emap_n = deepcopy(temp_emap_n.array())

        vmf          = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains())
        bmf          = d.MeshFunction("size_t", bmesh, surface_dim)
        vmf_combined = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains())
        bmf_combined = d.MeshFunction("size_t", bmesh, surface_dim)

        # iterate through facets of bmesh (transfer markers from volume mesh function to boundary mesh function)
        for idx, facet in enumerate(d.entities(bmesh,surface_dim)): 
            vmesh_idx = bmesh_emap_n[idx] # get the index of the face on vmesh corresponding to this face on bmesh
            vmesh_boundarynumber = vmf.array()[vmesh_idx] # get the value of the mesh function at this face
            bmf.array()[idx] = vmesh_boundarynumber # set the value of the boundary mesh function to be the same value

        # combine markers for subdomains specified as a list of markers
        for comp_name, comp in self.items:
            if type(comp.cell_marker) == list:
                if not all([type(x)==int for x in comp.cell_marker]):
                    raise ValueError("Cell markers were given as a list but not all elements were ints.")

                first_index_marker = comp.cell_marker[0] # combine into the first marker of the list 
                comp.first_index_marker = first_index_marker
                Print(f"Combining markers {comp.cell_marker} (for compartment {comp_name}) into single marker {first_index_marker}.")
                for marker_value in comp.cell_marker:
                    vmf_combined.array()[vmf.array() == marker_value] = first_index_marker
                    bmf_combined.array()[bmf.array() == marker_value] = first_index_marker
            elif type(comp.cell_marker) == int:
                comp.first_index_marker = comp.cell_marker
                vmf_combined.array()[vmf.array() == comp.cell_marker] = comp.cell_marker
                bmf_combined.array()[bmf.array() == comp.cell_marker] = comp.cell_marker
            else:
                raise ValueError("Cell markers must either be provided as an int or list of ints")


        # Loop through compartments: extract submeshes and integration measures
        for comp_name, comp in self.items:
            # FEniCS doesn't allow parallelization of SubMeshes. We need
            # SubMeshes because one boundary will often have multiple domains of
            # interest with different species (e.g., PM, ER). By exporting the
            # submeshes in serial we can reload them back in in parallel.

            if comp_name!=main_mesh_str and comp.dimensionality==surface_dim:
                # # TODO: fix this (parallel submesh)
                # if size > 1: # if we are running in parallel
                #     Print("CPU %d: Loading submesh for %s from file" % (rank, comp_name))
                #     submesh = d.Mesh(d.MPI.comm_self, 'submeshes/submesh_' + comp.name + '_' + str(comp.cell_marker) + '.xml')
                #     self.meshes[comp_name] = submesh
                #     comp.mesh = submesh
                # else:
                submesh = d.SubMesh(bmesh, bmf_combined, comp.first_index_marker)
                self.vertex_mappings[comp_name] = submesh.data().array("parent_vertex_indices", 0)
                self.meshes[comp_name] = submesh
                comp.mesh = submesh

                # # TODO: fix this (parallel submesh)
                # if save_to_file:
                #     Print("Saving submeshes %s for use in parallel" % comp_name)
                #     save_str = 'submeshes/submesh_' + comp.name + '_' + str(comp.cell_marker) + '.xml'
                #     d.File(save_str) << submesh

            # integration measures
            if comp.dimensionality==main_mesh.dimensionality:
                comp.ds = d.Measure('ds', domain=comp.mesh, subdomain_data=vmf_combined, metadata={'quadrature_degree': 3})
                comp.ds_uncombined = d.Measure('ds', domain=comp.mesh, subdomain_data=vmf, metadata={'quadrature_degree': 3})
                comp.dP = None
            elif comp.dimensionality<main_mesh.dimensionality:
                comp.dP = d.Measure('dP', domain=comp.mesh)
                comp.ds = None
            else:
                raise Exception("main_mesh is not a maximum dimension compartment")
            comp.dx = d.Measure('dx', domain=comp.mesh, metadata={'quadrature_degree': 3})

        # Get # of vertices
        for key, mesh in self.meshes.items():
            num_vertices = mesh.num_vertices()
            print('CPU %d: My partition of mesh %s has %d vertices' % (rank, key, num_vertices))
            self[key].num_vertices = num_vertices

        self.bmesh          = bmesh
        self.bmesh_emap_0   = bmesh_emap_0
        self.bmesh_emap_n   = bmesh_emap_n
        self.mesh_functions = {
                                'vmf': vmf,
                                'bmf': bmf,
                                'vmf_combined': vmf_combined,
                                'bmf_combined': bmf_combined,
                              }

        # # TODO: fix this (parallel submesh)
        # # If we were running in serial to generate submeshes, exit here and
        # # restart in parallel
        # if save_to_file and size==1:
        #     Print("If run in serial, submeshes were saved to file. Run again"\
        #           "in parallel.")
        #     exit()

    def extract_submeshes_refactor(self, parent_mesh):
        # Get minimum and maximum dimensions of meshes being computed on.
        volume_dim  = self.max_dim
        surface_dim = self.min_dim
        # Check that dimensionality of components and mesh is acceptable
        if volume_dim != parent_mesh.dimensionality:
            raise ValueError(f"Parent mesh has geometric dimension: {parent_mesh.dolfin_mesh.geometric_dimension()} which"
                            +f" is not the same as volume_dim: {volume_dim}.")

        # Define mesh functions
        #volume_mf = d.MeshFunction('size_t', parent_mesh.dolfin_mesh, volume_dim, 

        # Get volume and boundary mesh
        #self[main_mesh_str].mesh   = self.meshes[main_mesh_str]
        smesh           = d.BoundaryMesh(parent_mesh.dolfin_mesh, "exterior")

        # When smesh.entity_map() is called together with .array() it will return garbage values. We should only call 
        # entity_map once to avoid this
        temp_emap_0     = smesh.entity_map(0)
        smesh_emap_0    = deepcopy(temp_emap_0.array()) # entity map to vertices
        temp_emap_n     = smesh.entity_map(surface_dim)
        smesh_emap_n    = deepcopy(temp_emap_n.array()) # entity map to facets

        # Mesh functions
        # 
        # vvmf: cell markers for volume mesh. Used to distinguish sub-volumes
        #
        #
        #
        #vvmf         = d.MeshFunction("size_t", vmesh, volume_dim, vmesh.domains())  # cell markers for volume mesh
        #vsmf         = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains()) # facet markers for volume mesh
        #smf          = d.MeshFunction("size_t", bmesh, surface_dim)                  # cell markers for surface mesh
        #vmf_combined = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains()) # 
        #bmf_combined = d.MeshFunction("size_t", bmesh, surface_dim)

        vmf          = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains())
        bmf          = d.MeshFunction("size_t", bmesh, surface_dim)
        vmf_combined = d.MeshFunction("size_t", vmesh, surface_dim, vmesh.domains())
        bmf_combined = d.MeshFunction("size_t", bmesh, surface_dim)

        # iterate through facets of bmesh (transfer markers from volume mesh function to boundary mesh function)
        for idx, facet in enumerate(d.entities(bmesh,surface_dim)): 
            vmesh_idx = bmesh_emap_n[idx] # get the index of the face on vmesh corresponding to this face on bmesh
            vmesh_boundarynumber = vmf.array()[vmesh_idx] # get the value of the mesh function at this face
            bmf.array()[idx] = vmesh_boundarynumber # set the value of the boundary mesh function to be the same value

        # combine markers for subdomains specified as a list of markers
        for comp_name, comp in self.items:
            if type(comp.cell_marker) == list:
                if not all([type(x)==int for x in comp.cell_marker]):
                    raise ValueError("Cell markers were given as a list but not all elements were ints.")

                first_index_marker = comp.cell_marker[0] # combine into the first marker of the list 
                comp.first_index_marker = first_index_marker
                Print(f"Combining markers {comp.cell_marker} (for compartment {comp_name}) into single marker {first_index_marker}.")
                for marker_value in comp.cell_marker:
                    vmf_combined.array()[vmf.array() == marker_value] = first_index_marker
                    bmf_combined.array()[bmf.array() == marker_value] = first_index_marker
            elif type(comp.cell_marker) == int:
                comp.first_index_marker = comp.cell_marker
                vmf_combined.array()[vmf.array() == comp.cell_marker] = comp.cell_marker
                bmf_combined.array()[bmf.array() == comp.cell_marker] = comp.cell_marker
            else:
                raise ValueError("Cell markers must either be provided as an int or list of ints")


        # Loop through compartments: extract submeshes and integration measures
        for comp_name, comp in self.items:
            # FEniCS doesn't allow parallelization of SubMeshes. We need
            # SubMeshes because one boundary will often have multiple domains of
            # interest with different species (e.g., PM, ER). By exporting the
            # submeshes in serial we can reload them back in in parallel.

            if comp_name!=main_mesh_str and comp.dimensionality==surface_dim:
                # # TODO: fix this (parallel submesh)
                # if size > 1: # if we are running in parallel
                #     Print("CPU %d: Loading submesh for %s from file" % (rank, comp_name))
                #     submesh = d.Mesh(d.MPI.comm_self, 'submeshes/submesh_' + comp.name + '_' + str(comp.cell_marker) + '.xml')
                #     self.meshes[comp_name] = submesh
                #     comp.mesh = submesh
                # else:
                submesh = d.SubMesh(bmesh, bmf_combined, comp.first_index_marker)
                self.vertex_mappings[comp_name] = submesh.data().array("parent_vertex_indices", 0)
                self.meshes[comp_name] = submesh
                comp.mesh = submesh

                # # TODO: fix this (parallel submesh)
                # if save_to_file:
                #     Print("Saving submeshes %s for use in parallel" % comp_name)
                #     save_str = 'submeshes/submesh_' + comp.name + '_' + str(comp.cell_marker) + '.xml'
                #     d.File(save_str) << submesh

            # integration measures
            if comp.dimensionality==volume_dim:
                comp.ds = d.Measure('ds', domain=comp.mesh, subdomain_data=vmf_combined, metadata={'quadrature_degree': 3})
                comp.ds_uncombined = d.Measure('ds', domain=comp.mesh, subdomain_data=vmf, metadata={'quadrature_degree': 3})
                comp.dP = None
            elif comp.dimensionality<volume_dim:
                comp.dP = d.Measure('dP', domain=comp.mesh)
                comp.ds = None
            else:
                raise Exception(f"Internal error: {comp_name} has a dimension larger than then the volume dimension.")
            comp.dx = d.Measure('dx', domain=comp.mesh, metadata={'quadrature_degree': 3})

        # Get # of vertices
        for key, mesh in self.meshes.items():
            num_vertices = mesh.num_vertices()
            print('CPU %d: My partition of mesh %s has %d vertices' % (rank, key, num_vertices))
            self[key].num_vertices = num_vertices

        self.bmesh          = bmesh
        self.bmesh_emap_0   = bmesh_emap_0
        self.bmesh_emap_n   = bmesh_emap_n
        self.mesh_functions = {
                                'vmf': vmf,
                                'bmf': bmf,
                                'vmf_combined': vmf_combined,
                                'bmf_combined': bmf_combined,
                              }

        # # TODO: fix this (parallel submesh)
        # # If we were running in serial to generate submeshes, exit here and
        # # restart in parallel
        # if save_to_file and size==1:
        #     Print("If run in serial, submeshes were saved to file. Run again"\
        #           "in parallel.")
        #     exit()

    def compute_scaling_factors(self):
        for key, comp in self.items:
            comp.scale_to = {}
            for key2, comp2 in self.items:
                if key != key2:
                    comp.scale_to.update({key2: comp.nvolume / comp2.nvolume})

@dataclass
class Compartment(ObjectInstance):
    name: str
    dimensionality: int
    compartment_units: pint.Unit
    cell_marker: int
    
    def __post_init__(self):
        self._convert_pint_quantity_to_unit()
        self._check_input_type_validity()
        self._convert_pint_unit_to_quantity()
        self.check_validity()
    
    def check_validity(self):
        if self.dimensionality not in [1,2,3]:
            raise ValueError(f"Compartment {self.name} has dimensionality {self.dimensionality}. Dimensionality must be in [1,2,3].")
        # checking units
        if not self.compartment_units.check('[length]'):
            raise ValueError(f"Compartment {self.name} has units of {self.compartment_units} - units must be dimensionally equivalent to [length].")

    def compute_nvolume(self):
        self.nvolume = d.assemble(d.Constant(1.0)*self.dx) * self.compartment_units ** self.dimensionality

    @property
    def dolfin_mesh(self):
        return self.mesh.dolfin_mesh



class ReactionContainer(ObjectContainer):
    def __init__(self):
        super().__init__(Reaction)

        #self.properties_to_print = ['name', 'lhs', 'rhs', 'eqn_f', 'eqn_r', 'param_map', 'reaction_type', 'explicit_restriction_to_domain', 'group']
        self.properties_to_print = ['name', 'lhs', 'rhs', 'eqn_f']#, 'eqn_r']

    def get_species_compartment_counts(self, sc, cc):
        """
        Returns a Counter object with the number of times a species appears in each compartment
        """
        self.do_to_all('get_involved_species_and_compartments', {"sc": sc, "cc": cc})
        all_involved_species = set([sp for species_set in [rxn.involved_species_link.values() for rxn in self.values] for sp in species_set])
        for sp_name, sp in sc.items:
            if sp in all_involved_species:
                sp.is_in_a_reaction = True

        compartment_counts = [sp.compartment_name for sp in all_involved_species]

        return Counter(compartment_counts)


    def reaction_to_fluxes(self):
        self.do_to_all('reaction_to_fluxes')
        flux_list = []
        for rxn in self.values:
            for f in rxn.flux_list:
                flux_list.append(f)
        self.flux_list = flux_list
    def get_flux_container(self):
        return FluxContainer(Dict=odict([(f.flux_name, f) for f in self.flux_list]))

@dataclass
class Reaction(ObjectInstance):
    name: str
    lhs: list
    rhs: list
    param_map: dict
    reaction_type: str='mass_action'
    species_map: dict = dataclasses.field(default_factory=dict)
    explicit_restriction_to_domain: str=''
    track_value: bool=False

    def __post_init__(self):
        self._check_input_type_validity()
        self.check_validity()

        # Finish initializing the species map
        for species_name in set(self.lhs + self.rhs):
            if species_name not in self.species_map:
                self.species_map[species_name] = species_name


    def check_validity(self):
        # Type checking
        if not all([isinstance(x, str) for x in self.lhs]):
            raise TypeError(f"Reaction {self.name} requires a list of strings as input for lhs.")
        if not all([isinstance(x, str) for x in self.rhs]):
            raise TypeError(f"Reaction {self.name} requires a list of strings as input for rhs.")
        if not all([type(k)==str and type(v)==str for (k,v) in self.param_map.items()]):
            raise TypeError(f"Reaction {self.name} requires a dict of str:str as input for param_map.")
        if self.species_map:
            if not all([k==str and v==str for (k,v) in self.species_map.items()]):
                raise TypeError(f"Reaction {self.name} requires a dict of str:str as input for species_map.")

    # def __init__(self, name, Dict=None, eqn_f_str=None, eqn_r_str=None,
    #              explicit_restriction_to_domain=False, species_map={}, track_value=False):
    #     if eqn_f_str:
    #         print("Reaction %s: using the specified equation for the forward flux: %s" % (name, eqn_f_str))
    #         self.eqn_f = parse_expr(eqn_f_str)
    #     if eqn_r_str:
    #         print("Reaction %s: using the specified equation for the reverse flux: %s" % (name, eqn_r_str))
    #         self.eqn_r = parse_expr(eqn_r_str)
    #     self.explicit_restriction_to_domain = explicit_restriction_to_domain
    #     self.track_value = track_value
    #     super().__init__(name, Dict)

    # def initialize_flux_equations_for_known_reactions(self, reaction_database={}):
    #     """
    #     Generates unsigned forward/reverse flux equations for common/known reactions
    #     """
    #     if self.reaction_type == 'mass_action':
    #         rxn_sym_str = self.param_map['on']
    #         for sp_name in self.lhs:
    #             rxn_sym_str += '*' + sp_name
    #         self.eqn_f = parse_expr(rxn_sym_str)

    #         rxn_sym_str = self.param_map['off']
    #         for sp_name in self.rhs:
    #             rxn_sym_str += '*' + sp_name
    #         self.eqn_r = parse_expr(rxn_sym_str)

    #     elif self.reaction_type == 'mass_action_forward':
    #         rxn_sym_str = self.param_map['on']
    #         for sp_name in self.lhs:
    #             rxn_sym_str += '*' + sp_name
    #         self.eqn_f = parse_expr(rxn_sym_str)

    #     elif self.reaction_type in reaction_database.keys():
    #         self._custom_reaction(reaction_database[self.reaction_type])

    #     else:
    #         raise Exception("Reaction %s does not seem to have an associated equation" % self.name)

    def _custom_reaction(self, sym_str):
        rxn_expr = parse_expr(sym_str)
        rxn_expr = rxn_expr.subs(self.param_map)
        rxn_expr = rxn_expr.subs(self.species_map)
        self.eqn_f = rxn_expr

    def reaction_to_fluxes(self):
        self.flux_list = []
        all_species = self.lhs + self.rhs
        unique_species = set(all_species)
        for species_name in unique_species:
            stoich = max([self.lhs.count(species_name), self.rhs.count(species_name)])
            #all_species.count(species_name)

            track = True if species_name == self.track_value else False

            if hasattr(self, 'eqn_f'):
                flux_name = self.name + '_f_' + species_name
                sign = -1 if species_name in self.lhs else 1
                signed_stoich = sign*stoich
                self.flux_list.append(Flux(flux_name, species_name, self.eqn_f, signed_stoich, self.involved_species_link,
                                          self.parameters, self.group, self, self.explicit_restriction_to_domain, track))
            if hasattr(self, 'eqn_r'):
                flux_name = self.name + '_r_' + species_name
                sign = 1 if species_name in self.lhs else -1
                signed_stoich = sign*stoich
                self.flux_list.append(Flux(flux_name, species_name, self.eqn_r, signed_stoich, self.involved_species_link,
                                          self.parameters, self.group, self, self.explicit_restriction_to_domain, track))



class FluxContainer(ObjectContainer):
    def __init__(self):
        super().__init__(Flux)

        # self.properties_to_print = ['species_name', 'sym_eqn', 'sign', 'involved_species',
        #                      'involved_parameters', 'source_compartment',
        #                      'destination_compartment', 'ukeys', 'group']

        self.properties_to_print = ['species_name', 'sym_eqn', 'signed_stoich', 'ukeys']#'source_compartment', 'destination_compartment', 'ukeys']

@dataclass
class Flux(ObjectInstance):
    flux_name: str
    species_name: str
    sym_eqn: sympy.Symbol
    signed_stoich: int
    species_map: dict
    param_map: dict
    group: str
    parent_reaction: Reaction
    explicit_restriction_to_domain: str=''
    track_value: bool=False

    def __post_init__(self):
        self.tracked_values = []
        self.sym_list = [str(x) for x in self.sym_eqn.free_symbols]
        self.lambda_eqn = sympy.lambdify(self.sym_list, self.sym_eqn, modules=['sympy','numpy'])
        self.involved_species = list(self.species_map.keys())
        self.involved_parameters = list(self.param_map.keys())

        self._check_input_type_validity()
        self.check_validity()
    
    def check_validity(self):
        pass

    def get_additional_flux_properties(self, cc, solver_system):
        # get additional properties of the flux
        self.get_involved_species_parameters_compartment(cc)
        self.get_flux_dimensionality()
        self.get_boundary_marker()
        self.get_flux_units()
        self.get_is_linear()
        self.get_is_linear_comp()
        self.get_ukeys(solver_system)
        self.get_integration_measure(cc, solver_system)

    def get_involved_species_parameters_compartment(self, cc):
        sym_str_list = {str(x) for x in self.sym_list}
        self.involved_species = sym_str_list.intersection(self.species_map.keys())
        self.involved_species.add(self.species_name)
        self.involved_parameters = sym_str_list.intersection(self.param_map.keys())

        # truncate species_map and param_map so they only contain the species and parameters we need
        self.species_map = dict((k, self.species_map[k]) for k in self.involved_species if k in self.species_map)
        self.param_map = dict((k, self.param_map[k]) for k in self.involved_parameters if k in self.param_map)

        self.involved_compartments = dict([(sp.compartment.name, sp.compartment) for sp in self.species_map.values()])

        if self.explicit_restriction_to_domain:
            self.involved_compartments.update({self.explicit_restriction_to_domain: cc[self.explicit_restriction_to_domain]})
        if len(self.involved_compartments) not in (1,2):
            raise Exception("Number of compartments involved in a flux must be either one or two!")
    #def flux_to_dolfin(self):

    def get_flux_dimensionality(self):
        destination_compartment = self.species_map[self.species_name].compartment
        destination_dim = destination_compartment.dimensionality
        comp_names = set(self.involved_compartments.keys())
        comp_dims = set([comp.dimensionality for comp in self.involved_compartments.values()])
        comp_names.remove(destination_compartment.name)
        comp_dims.remove(destination_dim)

        if len(comp_names) == 0:
            self.flux_dimensionality = [destination_dim]*2
            self.source_compartment = destination_compartment.name
        else:
            source_dim = comp_dims.pop()
            self.flux_dimensionality = [source_dim, destination_dim]
            self.source_compartment = comp_names.pop()

        self.destination_compartment = destination_compartment.name

    def get_boundary_marker(self):
        dim = self.flux_dimensionality
        if dim[1] <= dim[0]:
            self.boundary_marker = None
        elif dim[1] > dim[0]: # boundary flux
            self.boundary_marker = self.involved_compartments[self.source_compartment].first_index_marker

    def get_flux_units(self):
        sp = self.species_map[self.species_name]
        compartment_units = sp.compartment.compartment_units
        # a boundary flux
        if (self.boundary_marker and self.flux_dimensionality[1]>self.flux_dimensionality[0]):
            self.flux_units = sp.concentration_units / compartment_units * sp.D_units
        else:
            self.flux_units = sp.concentration_units / ureg.s

    def get_is_linear(self):
        """
        For a given flux we want to know which terms are linear
        """
        is_linear_wrt = {}
        for sym_var in self.sym_list:
            var_name = str(sym_var)
            if var_name in self.involved_species:
                if sympy.diff(self.sym_eqn, var_name , 2).is_zero:
                    is_linear_wrt[var_name] = True
                else:
                    is_linear_wrt[var_name] = False

        self.is_linear_wrt = is_linear_wrt

    def get_is_linear_comp(self):
        """
        Is the flux linear in terms of a compartment vector (e.g. dj/du['pm'])
        """
        is_linear_wrt_comp = {}
        umap = {}

        for var_name in self.sym_list:
            if var_name in self.involved_species:
                comp_name = self.species_map[var_name].compartment_name
                umap.update({var_name: 'u'+comp_name})

        new_eqn = self.sym_eqn.subs(umap)

        for comp_name in self.involved_compartments:
            if sympy.diff(new_eqn, 'u'+comp_name, 2).is_zero:
                is_linear_wrt_comp[comp_name] = True
            else:
                is_linear_wrt_comp[comp_name] = False

        self.is_linear_wrt_comp = is_linear_wrt_comp

    def get_integration_measure(self, cc, solver_system):
        sp = self.species_map[self.species_name]
        flux_dim = self.flux_dimensionality
        min_dim = min(cc.get_property('dimensionality').values())
        max_dim = max(cc.get_property('dimensionality').values())

        # boundary flux
        if flux_dim[0] < flux_dim[1]:
            self.int_measure = sp.compartment.ds(self.boundary_marker)
        # volumetric flux (max dimension)
        elif flux_dim[0] == flux_dim[1] == max_dim:
            self.int_measure = sp.compartment.dx
        # volumetric flux (min dimension)
        elif flux_dim[1] == min_dim < max_dim:
            if solver_system.ignore_surface_diffusion:
                self.int_measure = sp.compartment.dP
            else:
                self.int_measure = sp.compartment.dx
        else:
            raise Exception("I'm not sure what integration measure to use on a flux with this dimensionality")

    def get_ukeys(self, solver_system):
        """
        Given the dimensionality of a flux (e.g. 2d surface to 3d vol) and the dimensionality
        of a species, determine which term of u should be used
        """
        self.ukeys = {}
        flux_vars = [str(x) for x in self.sym_list if str(x) in self.involved_species]
        for var_name in flux_vars:
            self.ukeys[var_name] = self.get_ukey(var_name, solver_system)

    def get_ukey(self, var_name, solver_system):
        sp = self.species_map[self.species_name]
        var = self.species_map[var_name]

        if solver_system.nonlinear_solver.method == 'newton':
            # if var.dimensionality > sp.dimensionality:
            #     return 'b'+sp.compartment_name
            # else:
            #     return 'u'

            # Testing volume interpolated functions
            if var.dimensionality > sp.dimensionality:
                return 'b_'+sp.compartment_name
            elif var.dimensionality < sp.dimensionality:
                return 'v_'+sp.compartment_name
            else:
                return 'u'

        elif solver_system.nonlinear_solver.method == 'IMEX':
            ## same compartment
            # dynamic lhs
            # if var.name == sp.name:
            #     if self.is_linear_wrt[sp.name]:
            #         return 't'
            #     else:
            #         return 'n'
            # static lhs
            if var.compartment_name == sp.compartment_name:
                if self.is_linear_wrt_comp[sp.compartment_name]:
                    return 't'
                else:
                    return 'n'
            ## different compartments
            # volume -> surface
            if var.dimensionality > sp.dimensionality:
                return 'b_'+sp.compartment_name
            # surface -> volume is covered by first if statement in get_ukey()

        raise Exception("Missing logic in get_ukey(); contact a developer...")

    def flux_to_dolfin(self):
        value_dict = {}

        for var_name in [str(x) for x in self.sym_list]:
            if var_name in self.param_map.keys():
                var = self.param_map[var_name]
                if var.is_time_dependent:
                    value_dict[var_name] = var.dolfinConstant * var.unit
                else:
                    value_dict[var_name] = var.value_unit
            elif var_name in self.species_map.keys():
                var = self.species_map[var_name]
                ukey = self.ukeys[var_name]
                value_dict[var_name] = var.u[ukey]

                value_dict[var_name] *= var.concentration_units * 1

        eqn_eval = self.lambda_eqn(**value_dict)
        prod = eqn_eval.magnitude
        unit_prod = 1 * (1*eqn_eval.units).units
        #unit_prod = self.lambda_eqn(**unit_dict)
        #unit_prod = 1 * (1*unit_prod).units # trick to make object a "Quantity" class

        self.prod = prod
        self.unit_prod = unit_prod

class FormContainer:
    def __init__(self):
        self.form_list = []
    def add(self, new_form):
        self.form_list.append(new_form)
    def select_by(self, selection_key, value):
        return [f for f in self.form_list if getattr(f, selection_key)==value]
    def inspect(self, form_list=None):
        if not form_list:
            form_list = self.form_list

        for index, form in enumerate(form_list):
            Print("Form with index %d from form_list..." % index)
            if form.flux_name:
                Print("Flux name: %s" % form.flux_name)
            Print("Species name: %s" % form.species_name)
            Print("Form type: %s" % form.form_type)
            form.inspect()


class Form:
    def __init__(self, dolfin_form, species, form_type, flux_name=None):
        # form_type:
        # 'M': transient/mass form (holds time derivative)
        # 'D': diffusion form
        # 'R': domain reaction forms
        # 'B': boundary reaction forms

        self.dolfin_form = dolfin_form
        self.species = species
        self.species_name = species.name
        self.compartment_name = species.compartment_name
        self.form_type = form_type
        self.flux_name = flux_name

    def inspect(self):
        integrals = self.dolfin_form.integrals()
        for index, integral in enumerate(integrals):
            Print(str(integral) + "\n")
