"""
Implementation of DuplicateChecker engine class to run duplicate records analysis.
"""

from typing import List, Optional, Union

from pandas import DataFrame

from core.warnings import Priority

from core import QualityEngine, QualityWarning
from utils.auxiliary import find_duplicate_columns


class DuplicateChecker(QualityEngine):
    "Engine for running analyis on duplicate records."

    def __init__(self,
                 df: DataFrame,
                 entities: List[Union[str, List[str]]] = None,
                 is_close: bool = False,
                 severity: Optional[str] = None):
        """
        Arguments:
            df (DataFrame): reference DataFrame used to run the DataQuality analysis.
            entities (List[Union[str, List[str]]]): entities relevant for duplicate analysis.
                Passing lists allows composed entities of multiple columns.
            is_close (bool): Pass True to use numpy.isclose instead of pandas.equals in column comparison.
            severity (str): Sets the logger warning threshold.
                Valid levels are [DEBUG, INFO, WARNING, ERROR, CRITICAL]."""
        super().__init__(df=df, severity=severity)
        self._entities = [] if entities is None else entities
        self._tests = ["exact_duplicates", "entity_duplicates", "duplicate_columns"]
        self._is_close = is_close

    @property
    def entities(self):
        "Property that returns the entities relevant for duplicates analysis."
        return self._entities

    @entities.setter
    def entities(self, entities: List[Union[str, List[str]]]):
        if not isinstance(entities, list):
            raise ValueError("Property 'entities' should be a list.")
        entities = self.__unique_entities(entities)
        assert all(entity in self.df.columns if isinstance(entity, str) else [
                   c in self.df.columns for c in entity] for entity in entities), "Given entities should exist as \
DataFrame's columns."
        self._entities = entities

    @staticmethod
    def __unique_entities(entities: List[Union[str, List[str]]]):
        """Returns entities list with only unique entities"""
        entities = set(entity if isinstance(entity, str) else entity[0] if len(
            entity) == 1 else tuple(entity) for entity in entities)
        return [entity if isinstance(entity, str) else list(entity) for entity in entities]

    @staticmethod
    def __get_duplicates(df: DataFrame):
        "Returns duplicate records."
        return df[df.duplicated()]

    @staticmethod
    def __get_entity_duplicates(df: DataFrame, entity: Union[str, List[str]]):
        "Returns the duplicate records aggregated by a given entity."
        return df.groupby(entity).apply(DuplicateChecker.__get_duplicates).reset_index(drop=True)

    def exact_duplicates(self):
        "Returns a DataFrame filtered for exact duplicate records."
        dups = self.__get_duplicates(self.df)  # Filter for duplicate instances
        if len(dups) > 0:
            self.store_warning(
                QualityWarning(
                    test=QualityWarning.Test.EXACT_DUPLICATES, category=QualityWarning.Category.DUPLICATES,
                    priority=Priority.P2, data=dups,
                    description=f"Found {len(dups)} instances with exact duplicate feature values."
                ))
        else:
            self._logger.info("No exact duplicates were found.")
            dups = None
        return dups

    def __provided_entity_dups(self, entity: Optional[Union[str, List[str]]] = None) -> dict:
        "Find duplicates for passed entity (simple or composed)."
        found_dups = {}
        dups = self.__get_entity_duplicates(self.df, entity)
        if len(dups) > 0:                        # if we have any duplicates
            self.store_warning(
                QualityWarning(
                    test='Entity Duplicates', category='Duplicates', priority=Priority.P2, data=dups,
                    description=f"Found {len(dups)} duplicates after grouping by entities."
                ))
            if isinstance(entity, str):
                entity = [entity]  # Makes logic the same for str or List[str] entities
            set_vals = set(dups[entity].apply(tuple, axis=1))
            if len(entity) > 1:
                entity_key = tuple(entity)  # Lists are not hashable, therefore cannot be dictionary keys
            else:
                # No need to store keys as tuples for single entities (single values)
                set_vals = [val[0] for val in set_vals]
                entity_key = entity[0]
            for val in set_vals:  # iterate on each entity with duplicates
                found_dups.setdefault(entity_key, {})[val] = dups[(dups[entity].values == val).all(axis=1)]
        return found_dups

    def entity_duplicates(self, entity: Optional[Union[str, List[str]]] = None):
        """Returns a dict of {entity: {entity_value: duplicates}} of duplicate records after grouping by an entity.
        If entity is not specified, compute for all entities defined in the init.
        """
        ent_dups = {}
        if entity is not None:  # entity is specified
            ent_dups.update(self.__provided_entity_dups(entity))
        else:  # if entity is not specified
            if len(self.entities) == 0:
                self._logger.warning("There are no entities defined to run the analysis. Skipping the test.")
                return None

            for col in self.entities:
                ent_dups.update(self.entity_duplicates(col))

        return ent_dups

    def duplicate_columns(self):
        "Returns a mapping dictionary of columns with fully duplicated feature values."
        dups = find_duplicate_columns(self.df, self._is_close)
        cols_with_dups = len(dups.keys())
        if cols_with_dups > 0:
            self.store_warning(
                QualityWarning(
                    test=QualityWarning.Test.DUPLICATE_COLUMNS, category=QualityWarning.Category.DUPLICATES,
                    priority=Priority.P1, data=dups,
                    description=f"Found {cols_with_dups} columns with exactly the same feature values as other columns."
                )
            )
        else:
            self._logger.info("No duplicate columns were found.")
            dups = None
        return dups
