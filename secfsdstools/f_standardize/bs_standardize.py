from abc import ABC
from abc import abstractmethod
from typing import Dict, List, Tuple, Optional, Set

import numpy as np
import pandas as pd
import pandera as pa


class RuleEntity(ABC):

    @abstractmethod
    def get_input_tags(self) -> Set[str]:
        pass

    def process(self, df: pd.DataFrame):
        pass


class Rule(RuleEntity):

    @abstractmethod
    def get_target_tag(self) -> str:
        pass

    @abstractmethod
    def mask(self, df: pd.DataFrame) -> pa.typing.Series[bool]:
        pass

    @abstractmethod
    def apply(self, df: pd.DataFrame, mask: pa.typing.Series[bool]):
        pass

    def process(self, df: pd.DataFrame):
        self.apply(df, self.mask(df))


class RuleGroup(RuleEntity):
    """
    todo: to add -> automatische vergabe von Rule ID bezüglich Gruppe
    Alle Regeln müssten eigentlich vom selben Typ sein
    Müsste man also auf den konkreten Rule Typ typisieren.
    """

    def __init__(self, rules: List[RuleEntity], prefix: str):
        self.rules = rules
        self.prefix = prefix

    def process(self, df: pd.DataFrame):
        for rule in self.rules:
            rule.process(df)

    def get_input_tags(self) -> Set[str]:
        result: Set[str] = set()
        for rule in self.rules:
            result.update(rule.get_input_tags())
        return result


class RenameRule(Rule):

    def __init__(self, original: str, target: str):
        self.original = original
        self.target = target

    def mask(self, df: pd.DataFrame) -> pa.typing.Series[bool]:
        return (df[self.target].isna() &
                ~df[self.original].isna())

    def apply(self, df: pd.DataFrame, mask: pa.typing.Series[bool]):
        df.loc[mask, self.target] = df[self.original]

    def get_input_tags(self) -> Set[str]:
        return {self.target, self.original}

    def get_target_tag(self) -> str:
        return self.target


class MissingSumRule(Rule):

    def __init__(self, sum_name: str, summand_names: List[str]):
        self.sum_name = sum_name
        self.summand_names = summand_names

    def get_target_tag(self) -> str:
        return self.sum_name

    def get_input_tags(self) -> Set[str]:
        result = {self.sum_name}
        result.update(self.summand_names)
        return result

    def mask(self, df: pd.DataFrame) -> pa.typing.Series[bool]:
        # sum_name has to be not set and all summand_names have to be set
        mask = df[self.sum_name].isna()
        for summand_name in self.summand_names:
            mask = mask & ~df[summand_name].isna()

        return mask

    def apply(self, df: pd.DataFrame, mask: pa.typing.Series[bool]):
        df.loc[mask, self.sum_name] = df[self.summand_names].sum(axis=1)


class MissingSummandRule(Rule):

    def __init__(self, sum_name: str, missing_summand: str, existing_summands: List[str]):
        self.sum_name = sum_name
        self.missing_summand = missing_summand
        self.existing_summands = existing_summands

    def get_target_tag(self) -> str:
        return self.missing_summand

    def get_input_tags(self) -> Set[str]:
        result = {self.sum_name, self.missing_summand}
        result.update(self.existing_summands)
        return result

    def mask(self, df: pd.DataFrame) -> pa.typing.Series[bool]:
        # sum and other_summands must be set, missing_summand must not be set
        mask = ~df[self.sum_name].isna()
        for summand_name in self.existing_summands:
            mask = mask & ~df[summand_name].isna()
        mask = mask & df[self.missing_summand].isna()
        return mask

    def apply(self, df: pd.DataFrame, mask: pa.typing.Series[bool]):
        df.loc[mask, self.missing_summand] = \
            df[self.sum_name] - df[self.existing_summands].sum(axis=1)


class SumCompletionRuleGroupCreator:
    """
    completes the missing value of a simple addition, if one is missing.
    E.G Assets = AssetsCurrent + AssetsNoneCurrent
    """

    @staticmethod
    def create_group(sum_tag: str, summand_tags: List[str], prefix: str) -> RuleGroup:
        rules: List[RuleEntity] = []
        rules.append(MissingSumRule(sum_name=sum_tag,
                                    summand_names=summand_tags))
        for summand in summand_tags:
            others = summand_tags.copy()
            others.remove(summand)
            rules.append(MissingSummandRule(sum_name=sum_tag, missing_summand=summand,
                                            existing_summands=others))
        return RuleGroup(rules=rules, prefix=prefix)


class BalanceSheetStandardizer:
    """wichtig, nur für main optimiert, nicht für coregs"""

    bs_rename_rg = RuleGroup(
        rules=[
            RenameRule(original='AssetsNet', target='Assets'),
            RenameRule(
                original='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                target='Equity'),
            RenameRule(original='PartnersCapital', target='Equity'),
            RenameRule(original='StockholdersEquity', target='Equity'),
            RenameRule(original='CashAndCashEquivalentsAtCarryingValue', target='Cash'),
            RenameRule(original='RetainedEarningsAppropriated', target='RetainedEarnings'),
            RenameRule(original='RetainedEarningsAccumulatedDeficit', target='RetainedEarnings')
        ],
        prefix="BR"
    )

    # todo: CashOther wird noch nirgends verwendet
    # todo: das funktioniert so nicht, da nur summiert wird, falls alle summandspalten
    # nicht null sind -> es müsste noch eine spezielle Regel haben,
    # sum with existing summands oder so..
    bs_sumup_rg = RuleGroup(
        rules=[MissingSumRule(
            sum_name='CashOther',
            summand_names=[
                'CashAndCashEquivalentsAtFairValue',
                'CashAndDueFromBanks',
                'CashCashEquivalentsAndFederalFundsSold',
                'RestrictedCashAndCashEquivalentsAtCarryingValue',
                'CashAndCashEquivalentsInForeignCurrencyAtCarryingValue'])],
        prefix="SU"
    )

    bs_sum_completion = RuleGroup(
        prefix="SC",
        rules=[
            SumCompletionRuleGroupCreator.create_group(
                sum_tag='Assets',
                summand_tags=['AssetsCurrent', 'AssetsNoncurrent'],
                prefix="Ass"
            ),
            SumCompletionRuleGroupCreator.create_group(
                sum_tag='Liabilities',
                summand_tags=['LiabilitiesCurrent', 'LiabilitiesNoncurrent'],
                prefix="Lia"
            )
        ])

    # these are the columns that finally are returned after the standardization
    final_tags: List[str] = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                             'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
                             'Equity',
                             'InventoryNet',
                             'Cash',
                             'CashOther',
                             'RetainedEarnings'
                             ]

    # these are the relevant tags that we need to calculate missing values
    calculation_tags: List[str] = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                                   'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
                                   'Equity',
                                   'InventoryNet',
                                   'Cash',
                                   'CashOther',
                                   'RetainedEarnings',
                                   'LiabilitiesAndStockholdersEquity'
                                   ]

    final_col_order = ['adsh', 'coreg', 'report', 'ddate'] + final_tags

    def __init__(self, calculate_pre_stats: bool = False, filter_for_main_report: bool = False):
        self.calculate_pre_stats: bool = calculate_pre_stats
        self.filter_for_main_report = filter_for_main_report
        self.pre_stats: Optional[pd.Series] = None
        self.post_stats: Optional[pd.Series] = None
        self.stats: Optional[pd.DataFrame] = None

        self.rule_tree = RuleGroup(prefix="BS_",
                                   rules=[
                                       self.bs_rename_rg,
                                       self.bs_sumup_rg,
                                       self.bs_sum_completion,
                                   ])

    def standardize(self, df: pd.DataFrame, ) -> pd.DataFrame:
        all_input_tags = self.rule_tree.get_input_tags()

        cpy_df = df[['adsh', 'coreg', 'tag', 'version', 'ddate', 'uom', 'value', 'report', 'line',
                     'negating']][df.tag.isin(all_input_tags)].copy()

        # todo: wann muss negating berücksichtigt werden -> nach dem pivot fliegt es raus!

        # pivot the table, so that the tags are now columns
        # todo: folgende Zeile sollte nicht mehr notwendig sein, sobald alle Regeln implementiert sind
        expected_tags = all_input_tags.union(self.final_tags)
        pivot_df = self._pivot(df=cpy_df, expected_tags=expected_tags)

        if self.calculate_pre_stats:
            pre_pivot_df = pivot_df[self.final_col_order]
            if self.filter_for_main_report:
                pre_pivot_df = self._filter_pivot_for_main_reports(pre_pivot_df)
            self.pre_stats = self._calculate_stats(pivot_df=pre_pivot_df)
            self.pre_stats.name = "pre"

        # apply the rule_tree
        self.rule_tree.process(pivot_df)

        # todo: kann das auch ganz am anfang nach pivot gemacht werden? oder sollte man warten,
        # bis alles berechnet ist, damit auch die berechneten werte zählen?
        if self.filter_for_main_report:
            pivot_df = self._filter_pivot_for_main_reports(pivot_df)

        # create a meaningful order
        pivot_df = pivot_df[self.final_col_order].copy()

        self.post_stats = self._calculate_stats(pivot_df=pivot_df)
        self.post_stats.name = "post"

        total = len(pivot_df)
        self.stats = pd.DataFrame(self.post_stats)
        self.stats['post_rel'] = self.stats.post / total
        if self.calculate_pre_stats:
            self.stats = self.stats.join(self.pre_stats)
            self.stats['pre_rel'] = self.stats.pre / total
            self.stats['reduction'] = 1 - (self.stats.post / self.stats.pre)

        return pivot_df

    def _filter_pivot_for_main_reports(self, pivot_df: pd.DataFrame) -> pd.DataFrame:
        cpy_pivot_df = pivot_df.copy()

        cpy_pivot_df['nan_count'] = cpy_pivot_df[
            BalanceSheetStandardizerOld.main_columns].isna().sum(
            axis=1)
        cpy_pivot_df.sort_values(['adsh', 'coreg', 'nan_count'], inplace=True)
        cpy_pivot_df = cpy_pivot_df.groupby(['adsh', 'coreg']).last()
        cpy_pivot_df.reset_index(inplace=True)
        return cpy_pivot_df

    def _calculate_stats(self, pivot_df: pd.DataFrame) -> pd.DataFrame:
        return pivot_df[self.final_tags].isna().sum(axis=0)

    def _apply_rules(self, df: pd.DataFrame, rules: List[Rule]):
        for rule in rules:
            rule.process(df)

    def _pivot(self, df: pd.DataFrame, expected_tags: Set[str]) -> pd.DataFrame:
        # todo: um pivot zu optimieren, sollten zuerst nur die Tags gefiltert werden,
        # welche tatsächlich auch benützt werden, alles andere sollte herausgefiltert werden
        # das müsste über die Regeln geschehen und sollte automatisch berechnet werden sollen.

        # it is possible, that the same number appears multiple times in different lines,
        # therefore, duplicates have to be removed, otherwise pivot is not possible
        relevant_df = df[['adsh', 'coreg', 'report', 'tag', 'value', 'ddate']].drop_duplicates()

        duplicates_df = relevant_df[
            ['adsh', 'coreg', 'report', 'tag', 'ddate']].value_counts().reset_index()
        duplicates_df.rename(columns={0: 'count'}, inplace=True)
        duplicated_adsh = duplicates_df[duplicates_df['count'] > 1].adsh.unique().tolist()

        # todo: logging duplicated entries ...>
        relevant_df = relevant_df[~relevant_df.adsh.isin(duplicated_adsh)]

        pivot_df = relevant_df.pivot(index=['adsh', 'coreg', 'report', 'ddate'],
                                     columns='tag',
                                     values='value')
        pivot_df.reset_index(inplace=True)
        missing_cols = set(expected_tags) - set(pivot_df.columns)
        for missing_col in missing_cols:
            pivot_df[missing_col] = np.nan
        pivot_df['nan_count'] = np.nan
        return pivot_df


# there are pre-pivot and post-pivot rules ..
# in order to make a pre assesement on how many fields could be filled, we would need to have
# pivot run without applying any rules, just pivot and return the desired colums,
# or just the basic renaming ...
# but without going for changing default names

class BalanceSheetStandardizerOld:
    rename_map: Dict[str, str] = {
        'AssetsNet': 'Assets',
        'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest': 'Equity',
        'PartnersCapital': 'Equity',
        'StockholdersEquity': 'Equity',
        'CashAndCashEquivalentsAtCarryingValue': 'Cash',
        'RetainedEarningsAppropriated': 'RetainedEarnings',
        'RetainedEarningsAccumulatedDeficit': 'RetainedEarnings'
    }

    # several tag values are sumed upd into a new tag
    sum_list_map: Dict[str, List[str]] = {'CashOther': [
        'CashAndCashEquivalentsAtFairValue',
        'CashAndDueFromBanks',
        'CashCashEquivalentsAndFederalFundsSold',
        'RestrictedCashAndCashEquivalentsAtCarryingValue',
        'CashAndCashEquivalentsInForeignCurrencyAtCarryingValue']}

    # these are the relevant tags that we need to calculate missing values
    relevant_tags: List[str] = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                                'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
                                'Equity',
                                'InventoryNet',
                                'Cash',
                                'CashOther',
                                'RetainedEarnings',
                                'LiabilitiesAndStockholdersEquity'
                                ]

    # these are the columns that finally are returned after the standardization
    final_tags: List[str] = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                             'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
                             'Equity',
                             'InventoryNet',
                             'Cash',
                             'RetainedEarnings'
                             ]

    # used to evaluate if a report is a the main balancesheet report
    # inside a report, there can be several different tables (different report nr)
    # which stmt value is BS.
    # however, we might be only interested in the "major" BS report. Usually this is the
    # one which has the least nan in the following columns
    main_columns = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                    'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent']

    # sum definition, which is used to calculate missing values, if eithter the total
    # or one of the summand is missing
    sum_definition: Dict[str, Tuple[str, str]] = {
        'Assets': ('AssetsCurrent', 'AssetsNoncurrent'),
        'Liabilities': ('LiabilitiesCurrent', 'LiabilitiesNoncurrent')
    }

    def standardize(self, df: pd.DataFrame, only_return_main_coreg: bool = False,
                    filter_for_main_report: bool = False) -> pd.DataFrame:

        # todo: wann muss negating berücksichtigt werden?
        cpy_df = df[
            ['adsh', 'coreg', 'tag', 'version', 'ddate', 'uom', 'value', 'report', 'line',
             'negating']].copy()

        cpy_df.loc[cpy_df['coreg'].isna(), 'coreg'] = ''

        # rename tags
        self.rename_tags(cpy_df)

        # sum tags up into a new sum-tag
        cpy_df = self.handle_sum_map(cpy_df)

        # filter the columns, only us the columns we need for the next steps
        cpy_df = cpy_df[cpy_df.tag.isin(BalanceSheetStandardizerOld.relevant_tags)]

        # pivot the table, so that the tags are now columns
        pivot_df = self.pivot(cpy_df)

        # complete the total = sum1 + sum2 tripples based on the sum_definition
        self.complete_sums(pivot_df)

        # apply the final rules
        self.complete_special_rules(pivot_df)

        # check if only the main coreg shall be returned
        if only_return_main_coreg:
            pivot_df = pivot_df[pivot_df.coreg == '']

        # check if only the main BS report shall be returned
        if filter_for_main_report:
            pivot_df['nan_count'] = pivot_df[
                BalanceSheetStandardizerOld.main_columns].isna().sum(
                axis=1)
            pivot_df.sort_values(['adsh', 'coreg', 'nan_count'], inplace=True)
            pivot_df = pivot_df.groupby(['adsh', 'coreg']).last()
            pivot_df.reset_index(inplace=True)

        # create a meaningful order
        col_order = ['adsh', 'coreg', 'report', 'ddate'] + BalanceSheetStandardizerOld.final_tags
        return pivot_df[col_order].copy()

    def rename_tags(self, df: pd.DataFrame):
        """ renames AssetsNet to Assets"""
        for old_tag, new_tag in BalanceSheetStandardizerOld.rename_map.items():
            mask = (df.tag == old_tag)
            df.loc[mask, 'tag'] = new_tag

    def handle_sum_map(self, df: pd.DataFrame) -> pd.DataFrame:
        append_list: List[pd.DataFrame] = []
        append_list.append(df)
        for tag, sum_list in BalanceSheetStandardizerOld.sum_list_map.items():
            result_df = df[df.tag.isin(sum_list)][['adsh', 'coreg', 'report', 'ddate', 'value']] \
                .groupby(['adsh', 'coreg', 'report', 'ddate']).sum().reset_index()
            result_df['tag'] = tag
            result_df['line'] = 0
            result_df['negating'] = 0
            result_df['uom'] = ''
            result_df['version'] = ''
            append_list.append(result_df)

        return pd.concat(append_list).reset_index()

    def pivot(self, df: pd.DataFrame) -> pd.DataFrame:
        # it is possible, that the same number appears multiple times in different lines,
        # therefore, duplicates have to be removed, otherwise pivot is not possible
        relevant_df = df[['adsh', 'coreg', 'report', 'tag', 'value', 'ddate']].drop_duplicates()

        duplicates_df = relevant_df[
            ['adsh', 'coreg', 'report', 'tag', 'ddate']].value_counts().reset_index()
        duplicates_df.rename(columns={0: 'count'}, inplace=True)
        duplicated_adsh = duplicates_df[duplicates_df['count'] > 1].adsh.unique().tolist()

        # todo: logging duplicated entries ...>
        relevant_df = relevant_df[~relevant_df.adsh.isin(duplicated_adsh)]

        pivot_df = relevant_df.pivot(index=['adsh', 'coreg', 'report', 'ddate'],
                                     columns='tag',
                                     values='value')
        pivot_df.reset_index(inplace=True)
        missing_cols = set(BalanceSheetStandardizerOld.relevant_tags) - set(pivot_df.columns)
        for missing_col in missing_cols:
            pivot_df[missing_col] = np.nan

        return pivot_df

    def _basic_sum_completion(self, df: pd.DataFrame, total: str, summand_1: str,
                              summand_2: str):
        """
            calculates missing summaries total = summand_1 + summand_2, if one of them is missing
        """

        mask_total_sum1_nosum2 = (~df[total].isna() &
                                  ~df[summand_1].isna() &
                                  df[summand_2].isna())
        df.loc[mask_total_sum1_nosum2, summand_2] = df[total] - df[summand_1]

        mask_total_nosum1_sum2 = (~df[total].isna() &
                                  df[summand_1].isna() &
                                  ~df[summand_2].isna())
        df.loc[mask_total_nosum1_sum2, summand_1] = df[total] - df[summand_2]

        mask_nototal_sum1_sum2 = (df[total].isna() &
                                  ~df[summand_1].isna() &
                                  ~df[summand_2].isna())
        df.loc[mask_nototal_sum1_sum2, total] = df[summand_1] + df[summand_2]

    def complete_sums(self, df: pd.DataFrame):
        """ completes sum definitions:
            eg. Assets = 'AssetsCurrent' + 'AssetsNoncurrent'
            if Assets and AssetsCurrent is present -> calculate AssetsNoncurrent
            if Assets and AssetsNoncurrent is present -> calculate AssetsCurrent
            if AssetsNoncurrent and AssetsCurrent are present, calculate Assets
        """
        for total, summands in BalanceSheetStandardizerOld.sum_definition.items():
            summand_1 = summands[0]
            summand_2 = summands[1]

            self._basic_sum_completion(df, total=total, summand_1=summand_1,
                                       summand_2=summand_2)

    def fill_still_isna_summands(self, df: pd.DataFrame):
        """ if we are left with unset summands"""

        for total, summands in BalanceSheetStandardizerOld.sum_definition.items():
            summand_1 = summands[0]
            summand_2 = summands[1]

            # if only the total is present, we assume that only the first summand (eg. currentassets are present)
            # that is not really proper.
            mask_total_nosum1_nosum2 = (~df[total].isna() &
                                        df[summand_1].isna() &
                                        df[summand_2].isna())
            df.loc[mask_total_nosum1_nosum2, summand_1] = df[total]
            df.loc[mask_total_nosum1_nosum2, summand_2] = 0.0

            # if only the first summand is present, wie assume that the total is equal to the first summand
            # and that the second summand is 0
            mask_nototal_sum1_nosum2 = (df[total].isna() &
                                        ~df[summand_1].isna() &
                                        df[summand_2].isna())
            df.loc[mask_nototal_sum1_nosum2, total] = df[summand_1]
            df.loc[mask_nototal_sum1_nosum2, summand_2] = 0.0

            # if only the second summand is present, wie assume that the total is equal to the second summand
            # and that the first  summand is 0
            mask_nototal_nosum1_sum2 = (df[total].isna() &
                                        df[summand_1].isna() &
                                        ~df[summand_2].isna())
            df.loc[mask_nototal_nosum1_sum2, total] = df[summand_2]
            df.loc[mask_nototal_nosum1_sum2, summand_1] = 0.0

    def complete_special_rules(self, df: pd.DataFrame):
        """
        Special rules which help to complete the information
        """

        self._basic_sum_completion(df, total='Assets', summand_1='Liabilities',
                                   summand_2='Equity')

        # actually, LiabilitiesAndStockholdersEquity should have the same value as Assets
        self._basic_sum_completion(df, total='LiabilitiesAndStockholdersEquity',
                                   summand_1='Liabilities',
                                   summand_2='Equity')

        # run complete sum again, since total fields could be present now
        self.complete_sums(df)
        self.fill_still_isna_summands(df)

        # if Equity == -Liabilities and Assets is nan, then
        # Assets, AssetsCurrent, and AssetsNoncurrent is 0.0
        mask = (df.Equity == -df.Liabilities) & df.Assets.isna()
        df.loc[mask, 'Assets'] = 0.0
        df.loc[mask, 'AssetsCurrent'] = 0.0
        df.loc[mask, 'AssetsNoncurrent'] = 0.0

        # if Cash is not set, then use CashOther to set Cash
        mask = df.Cash.isna()
        df.loc[mask, 'Cash'] = df.CashOther

        # set to zero
        mask = df.InventoryNet.isna()
        df.loc[mask, 'InventoryNet'] = 0.0
