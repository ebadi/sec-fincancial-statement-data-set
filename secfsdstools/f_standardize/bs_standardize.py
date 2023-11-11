from typing import List, Optional, Set

import numpy as np
import pandas as pd

from secfsdstools.f_standardize.base_rules import CopyTagRule, SumUpRule, SetSumIfOnlyOneSummand, \
    PostCopyToFirstSummand, PreSumUpCorrection, missingsumparts_rules_creator
from secfsdstools.f_standardize.base_rule_framework import RuleGroup
from secfsdstools.f_standardize.base_validation_rules import SumValidationRule


class RuleProcessor:
    identifier_tags = ['adsh', 'coreg', 'report', 'ddate']

    # todo
    # missing
    # preprocess
    # rules
    # group / list

    def __init__(self,
                 pre_rule_tree: RuleGroup,
                 rule_tree: RuleGroup,
                 post_rule_tree: RuleGroup,
                 validation_rules: List[ValidationRule],
                 iterations: int, main_tags: List[str], final_tags: List[str],
                 filter_for_main_report: bool = True, invert_negated: bool = True):
        self.rule_tree = rule_tree
        self.clean_up_rule_tree = clean_up_rule_tree
        self.validation_rules = validation_rules
        self.iterations = iterations
        self.main_tags = main_tags
        self.final_tags = final_tags
        self.filter_for_main_report = filter_for_main_report
        self.invert_negated = invert_negated

        self.final_col_order = self.identifier_tags + self.final_tags

        self.preprocess_dupliate_log_df: Optional[pd.DataFrame] = None
        self.log_df: Optional[pd.DataFrame] = None
        self.applied_rules_sum_df: Optional[pd.DataFrame] = None
        self.stats: Optional[pd.DataFrame] = None

    def get_ruletree_descriptions(self):
        # todo
        pass

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        all_input_tags = self.rule_tree.get_input_tags()

        relevant_df = \
            df[['adsh', 'coreg', 'tag', 'version', 'ddate', 'uom', 'value', 'report', 'line',
                'negating']][df.tag.isin(all_input_tags)]

        # preprocessing ..
        #  - deduplicate
        cpy_df = self._deduplicate(relevant_df).copy()

        #  - invert_negated
        if self.invert_negated:
            cpy_df.loc[cpy_df.negating == 1, 'value'] = -cpy_df.value

        # pivot the table, so that the tags become columns
        # todo: folgende Zeile sollte nicht mehr notwendig sein, sobald alle Regeln implementiert sind
        expected_tags = all_input_tags.union(self.final_tags)
        pivot_df = self._pivot(df=cpy_df, expected_tags=expected_tags)

        if self.filter_for_main_report:
            pivot_df = self._filter_pivot_for_main_reports(pivot_df)

        pivot_df_index_cols = ['adsh', 'coreg', 'report', 'ddate', 'uom']
        self.log_df = pivot_df[pivot_df_index_cols].copy()

        total_length = len(pivot_df)

        # calculate_pre_stats:
        pre_apply_df = pivot_df[self.final_col_order]
        self.pre_stats = self._calculate_stats(pivot_df=pre_apply_df)
        self.pre_stats.name = "pre"

        self.stats = pd.DataFrame(self.pre_stats)
        self.stats['pre_rel'] = self.stats.pre / total_length

        self.stats = pd.DataFrame(self.pre_stats)

        for i in range(self.iterations):
            # set ids of the rules in the tree, use the iteration number as prefix
            self.rule_tree.set_id(parent_prefix=f"{i}_")

            # apply the rule_tree
            self.rule_tree.process(df=pivot_df, log_df=self.log_df)

            self.post_stats = self._calculate_stats(pivot_df=pivot_df)
            self.post_stats.name = f"post_{i}"

            self.stats = self.stats.join(self.post_stats)
            self.stats[self.post_stats.name + '_rel'] = \
                self.stats[self.post_stats.name] / total_length
            self.stats[self.post_stats.name + '_red'] = \
                1 - (self.stats[self.post_stats.name] / self.stats.pre)

        # clean up rules
        self.clean_up_rule_tree.process(df=pivot_df, log_df=self.log_df)

        # calculate cleanup stats
        self.post_cleanup = self._calculate_stats(pivot_df=pivot_df)
        self.post_cleanup.name = "cleanup"
        self.stats = self.stats.join(self.post_cleanup)
        self.stats[self.post_cleanup.name + '_rel'] = \
            self.stats[self.post_cleanup.name] / total_length
        self.stats[self.post_cleanup.name + '_red'] = \
            1 - (self.stats[self.post_cleanup.name] / self.stats.pre)

        # create a meaningful order
        pivot_df = pivot_df[self.final_col_order].copy()

        # apply validation rules
        for validation_rule in self.validation_rules:
            validation_rule.validate(pivot_df)

        # caculate log_df summaries
        if self.log_df is not None:
            # filter for rule columns but making sure the order stays the same
            rule_columns = [x for x in self.log_df.columns if x not in pivot_df_index_cols]
            self.applied_rules_sum_df = self.log_df[rule_columns].sum()

        return pivot_df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        # find duplicated entries
        # sometimes, only single tags are duplicated, however, there are also reports
        # where all tags of a report are duplicated, maybe due to a problem with processing
        duplicates_s = \
            df.duplicated(['adsh', 'coreg', 'report', 'uom', 'tag', 'version', 'ddate', 'value'])

        self.preprocess_dupliate_log_df = df[duplicates_s] \
            [['adsh', 'coreg', 'report', 'tag', 'uom', 'version', 'ddate']].copy()

        return df[~duplicates_s]

    def _filter_pivot_for_main_reports(self, pivot_df: pd.DataFrame) -> pd.DataFrame:
        """ Some reports have more than one 'report number' (column report) for a
            certain statement. Generally, the one with the most tags is the one to take.
            This method operates on the pivoted data and counts the none-values of the
            "main columns". The main columns are the fields, that generally should be there.
             """

        cpy_pivot_df = pivot_df.copy()

        cpy_pivot_df['nan_count'] = cpy_pivot_df[self.main_tags].isna().sum(axis=1)
        cpy_pivot_df.sort_values(['adsh', 'coreg', 'nan_count'], inplace=True)
        cpy_pivot_df = cpy_pivot_df.groupby(['adsh', 'coreg']).last()
        cpy_pivot_df.reset_index(inplace=True)
        return cpy_pivot_df

    def _calculate_stats(self, pivot_df: pd.DataFrame) -> pd.DataFrame:
        return pivot_df[self.final_tags].isna().sum(axis=0)

    def _pivot(self, df: pd.DataFrame, expected_tags: Set[str]) -> pd.DataFrame:
        # it is possible, that the same number appears multiple times in different lines,
        # therefore, duplicates have to be removed, otherwise pivot is not possible
        relevant_df = df[
            ['adsh', 'coreg', 'report', 'tag', 'value', 'uom', 'ddate']].drop_duplicates()

        pivot_df = relevant_df.pivot(index=['adsh', 'coreg', 'report', 'uom', 'ddate'],
                                     columns='tag',
                                     values='value')
        pivot_df.reset_index(inplace=True)
        missing_cols = set(expected_tags) - set(pivot_df.columns)
        for missing_col in missing_cols:
            pivot_df[missing_col] = np.nan
        pivot_df['nan_count'] = np.nan
        return pivot_df


class BalanceSheetStandardizer(RuleProcessor):
    """
    The goal of this Standardizer is to create BalanceSheets that are compareable,
    meaning that they have the same tags.

    At the end, the standardized BS contains the following columns
    Assets
       AssetsCurrent
           Cash
       AssetsNoncurrent
    Liabilities
       LiabilitiesCurrent
       LiabilitiesNoncurrent
    OwnerEquity
        PaidInCapital
        RetainedEarnings
    LiabilitiesAndOwnerEquity

    """

    bs_rename_rg = RuleGroup(
        rules=[
            # sometimes, the total Assets is contained in the AssetsNet tag
            CopyTagRule(original='AssetsNet', target='Assets'),
            # either there is a StockholderEquity tag or a PartnersCapital tag,
            # but both to never appear together
            CopyTagRule(original='PartnersCapital', target='OwnerEquity'),
            CopyTagRule(original='StockholdersEquity', target='OwnerEquity'),
            CopyTagRule(original='CashAndCashEquivalentsAtCarryingValue', target='Cash'),
            CopyTagRule(original='LiabilitiesAndStockholdersEquity',
                        target='LiabilitiesAndOwnerEquity')

            # RenameRule(
            #     original='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            #     target='Equity'),
            # RenameRule(original='RetainedEarningsAppropriated', target='RetainedEarnings'),
            # RenameRule(original='RetainedEarningsAccumulatedDeficit', target='RetainedEarnings')
        ],
        prefix="BR"
    )

    # todo: CashOther wird noch nirgends verwendet
    bs_sumup_rg = RuleGroup(
        rules=[SumUpRule(
            sum_tag='CashOther',
            potential_summands=[
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
            *missingsumparts_rules_creator(
                sum_tag='Assets',
                summand_tags=['AssetsCurrent', 'AssetsNoncurrent']
            ),
            SetSumIfOnlyOneSummand(
                sum_tag='Assets',
                summand_set='AssetsCurrent',
                summands_nan=['AssetsNoncurrent']
            ),
            SetSumIfOnlyOneSummand(
                sum_tag='Assets',
                summand_set='AssetsNoncurrent',
                summands_nan=['AssetsCurrent']
            ),
            *missingsumparts_rules_creator(
                sum_tag='Liabilities',
                summand_tags=['LiabilitiesCurrent', 'LiabilitiesNoncurrent']
            ),
            SetSumIfOnlyOneSummand(
                sum_tag='Liabilities',
                summand_set='LiabilitiesCurrent',
                summands_nan=['LiabilitiesNoncurrent']
            ),
            SetSumIfOnlyOneSummand(
                sum_tag='Liabilities',
                summand_set='LiabilitiesNoncurrent',
                summands_nan=['LiabilitiesCurrent']
            ),
            *missingsumparts_rules_creator(
                sum_tag='AssLiaOwe',
                summand_tags=['Liabilities', 'OwnerEquity']
            ),
            *missingsumparts_rules_creator(
                sum_tag='LiabilitiesAndOwnerEquity',
                summand_tags=['Liabilities', 'OwnerEquity']
            )
        ])

    rule_tree = RuleGroup(prefix="BS_",
                          rules=[
                              bs_rename_rg,
                              bs_sumup_rg,
                              bs_sum_completion,
                          ])

    cleanup_rule_tree = RuleGroup(prefix="BS_POST",
                                  rules=[
                                      PostCopyToFirstSummand(sum_tag='Assets',
                                                             first_summand='AssetsCurrent',
                                                             other_summands=[
                                                                 'AssetsNoncurrent']),
                                      PostCopyToFirstSummand(sum_tag='Liabilities',
                                                             first_summand='LiabilitiesCurrent',
                                                             other_summands=[
                                                                 'LiabilitiesNoncurrent'])])
    proprocess_rule_tree = RuleGroup(prefix="BS_PRE",
                                     rules=[
                                         PreSumUpCorrection(sum_tag='Assets',
                                                            mixed_up_summand='AssetsNoncurrent',
                                                            other_summand='AssetsCurrent'),
                                         PreSumUpCorrection(sum_tag='Assets',
                                                            mixed_up_summand='AssetsCurrent',
                                                            other_summand='AssetsNoncurrent'),
                                     ])

    validation_rules: List[ValidationRule] = [
        SumValidationRule(id='AssetsCheck',
                          sum_tag='Assets',
                          summands=['AssetsCurrent', 'AssetsNoncurrent']),
        SumValidationRule(id='LiabilitiesCheck',
                          sum_tag='Liabilities',
                          summands=['LiabilitiesCurrent', 'LiabilitiesNoncurrent'])
    ]

    # these are the columns that finally are returned after the standardization
    final_tags: List[str] = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                             'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent',
                             'OwnerEquity', 'LiabilitiesAndOwnerEquity',
                             'InventoryNet',
                             'Cash',
                             'CashOther',
                             'RetainedEarnings'
                             ]

    # used to evaluate if a report is the main balancesheet report
    # inside a report, there can be several different tables (different report nr)
    # which stmt value is BS.
    # however, we might be only interested in the "major" BS report. Usually this is the
    # one which has the least nan in the following columns
    main_tags = ['Assets', 'AssetsCurrent', 'AssetsNoncurrent',
                 'Liabilities', 'LiabilitiesCurrent', 'LiabilitiesNoncurrent']

    def __init__(self, filter_for_main_report: bool = False, iterations: int = 3):
        super().__init__(rule_tree=self.rule_tree,
                         clean_up_rule_tree=self.cleanup_rule_tree,
                         validation_rules=self.validation_rules,
                         iterations=iterations,
                         main_tags=self.main_tags, final_tags=self.final_tags,
                         filter_for_main_report=filter_for_main_report)


# there are pre-pivot and post-pivot rules ..
# in order to make a pre assesement on how many fields could be filled, we would need to have
# pivot run without applying any rules, just pivot and return the desired colums,
# or just the basic renaming ...
# but without going for changing default names

# man könnte noch checks einbauen, ob z.B. die Summen definition gültig sind,
# d.h., dass der Wert der Summe in etwa der Summe der Werte der Summanden entsprciht


class BalanceSheetStandardizerOld:

    def fill_still_isna_summands(self, df: pd.DataFrame):
        """ if we are left with unset summands"""

        # for:
        # 'Assets': ('AssetsCurrent', 'AssetsNoncurrent'),
        # 'Liabilities': ('LiabilitiesCurrent', 'LiabilitiesNoncurrent')
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

        # self._basic_sum_completion(df, total='Assets', summand_1='Liabilities',
        #                            summand_2='Equity')
        #
        # # actually, LiabilitiesAndStockholdersEquity should have the same value as Assets
        # self._basic_sum_completion(df, total='LiabilitiesAndStockholdersEquity',
        #                            summand_1='Liabilities',
        #                            summand_2='Equity')

        # run complete sum again, since total fields could be present now
        # for:
        # 'Assets': ('AssetsCurrent', 'AssetsNoncurrent'),
        # 'Liabilities': ('LiabilitiesCurrent', 'LiabilitiesNoncurrent')
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
