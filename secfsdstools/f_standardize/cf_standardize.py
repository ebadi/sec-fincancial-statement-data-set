"""Contains the definitions to standardize incaome statements."""
from typing import List

from secfsdstools.f_standardize.base_prepivot_rules import PrePivotDeduplicate
from secfsdstools.f_standardize.base_rule_framework import RuleGroup
from secfsdstools.f_standardize.base_rules import CopyTagRule, SumUpRule, PostSetToZero, \
    MissingSumRule
from secfsdstools.f_standardize.base_validation_rules import ValidationRule, SumValidationRule
from secfsdstools.f_standardize.standardizing import Standardizer


class CashFlowStandardizer(Standardizer):
    """
    The goal of this Standardizer is to create CashFlow statements that are comparable,
    meaning that they have the same tags.

    At the end, the standardized CF contains the following columns

    <pre>

    Final Tags
        NetCashProvidedByUsedInOperatingActivities
        1.1. AdjustmentsToReconcileNetIncomeLossToCashProvidedByUsedInOperatingActivities
        1.1.1. DepreciationDepletionAndAmortization
        1.1.2. DeferredIncomeTaxExpenseBenefit
        1.1.3. ShareBasedCompensation
        1.1.7. IncreaseDecreaseInAccountsPayable
        1.1.8. IncreaseDecreaseInAccruedLiabilities
        1.2. OtherAdjustmentsToCashProvidedByUsedInOperatingActivities
        1.2.2. InterestPaidNet
        1.2.3. IncomeTaxesPaidNet

        NetCashProvidedByUsedInInvestingActivities
        2.1. Investments in Property, Plant, and Equipment
        2.1.1. PaymentsToAcquirePropertyPlantAndEquipment
        2.1.2. ProceedsFromSaleOfPropertyPlantAndEquipment
        2.2. Investments in Securities
        2.2.1. PaymentsToAcquireInvestments
        2.2.2. ProceedsFromSaleOfInvestments
        2.3. Business Acquisitions and Divestitures
        2.3.1. PaymentsToAcquireBusinessesNetOfCashAcquired
        2.3.2. ProceedsFromDivestitureOfBusinessesNetOfCashDivested
        2.4. OtherCashProvidedByUsedInInvestingActivities
        2.4.1. Investments in Intangible Assets
        2.4.1.1. PaymentsToAcquireIntangibleAssets
        2.4.1.2. ProceedsFromSaleOfIntangibleAssets

        NetCashProvidedByUsedInFinancingActivities
        3.1. Equity Transactions
        3.1.1. ProceedsFromIssuanceOfCommonStock
        3.1.4. PaymentsForRepurchaseOfCommonStock
        3.2. Debt Transactions
        3.2.1. ProceedsFromIssuanceOfDebt
        3.2.2. RepaymentsOfDebt
        3.3. Dividends
        3.3.1. DividendsPaid
        3.4. Leases
        3.4.1. PaymentsOfFinanceLeaseObligations
        3.5. Grants and Other Financing Sources
        3.5.1. ProceedsFromGovernmentGrants

        NetIncreaseDecreaseInCashAndCashEquivalents
        4.1. CashAndCashEquivalentsPeriodIncreaseDecrease
        4.2. EffectOfExchangeRateOnCashAndCashEquivalents


    Details
    1.    NetCashProvidedByUsedInOperatingActivities
    1.1.        AdjustmentsToReconcileNetIncomeLossToCashProvidedByUsedInOperatingActivities
    1.1.1.            DepreciationDepletionAndAmortization
    1.1.2.            DeferredIncomeTaxExpenseBenefit
    1.1.3.            ShareBasedCompensation
    1.1.4.            IncreaseDecreaseInAccountsReceivable
    1.1.5.            IncreaseDecreaseInInventories
    1.1.6.            IncreaseDecreaseInPrepaidDeferredExpenseAndOtherAssets
    1.1.7.            IncreaseDecreaseInAccountsPayable
    1.1.8.            IncreaseDecreaseInAccruedLiabilities
    1.1.9.            IncreaseDecreaseInOtherOperatingActivities
    1.1.10.           OtherNoncashIncomeExpense
    1.2.        OtherAdjustmentsToCashProvidedByUsedInOperatingActivities
    1.2.1.            NetIncomeLoss
    1.2.2.            InterestPaidNet
    1.2.3.            IncomeTaxesPaidNet
    1.2.4.            DividendsReceived
    1.2.5.            InterestReceived
    1.2.6.            IncreaseDecreaseInOperatingCapital
    1.2.7.            PaymentsForAssetRetirementObligations
    1.2.8.            PaymentsForProvisions
    1.2.9.            PaymentsForRestructuring

    2.   NetCashProvidedByUsedInInvestingActivities
    2.1.       Investments in Property, Plant, and Equipment
    2.1.1.           PaymentsToAcquirePropertyPlantAndEquipment
    2.1.2.           ProceedsFromSaleOfPropertyPlantAndEquipment
    2.2.      Investments in Securities
    2.2.1.           PaymentsToAcquireInvestments
    2.2.2.           ProceedsFromSaleOfInvestments
    2.2.3.           PaymentsToAcquireHeldToMaturitySecurities
    2.2.4.           ProceedsFromMaturitiesPrepaymentsAndCallsOfHeldToMaturitySecurities
    2.2.5.           PaymentsToAcquireAvailableForSaleSecurities
    2.2.6.           ProceedsFromSaleOfAvailableForSaleSecurities
    2.2.7.           PaymentsToAcquireTradingSecurities
    2.2.8.           ProceedsFromSaleOfTradingSecurities
    2.3.       Business Acquisitions and Divestitures
    2.3.1.           PaymentsToAcquireBusinessesNetOfCashAcquired
    2.3.2.           ProceedsFromDivestitureOfBusinessesNetOfCashDivested
    2.3.3.           PaymentsMadeInConnectionWithBusinessAcquisitions
    2.3.4.           ProceedsFromBusinessAcquisitionsNetOfCashAcquired
    2.4.       OtherCashProvidedByUsedInInvestingActivities
    2.4.1.           Investments in Intangible Assets
    2.4.1.1.              PaymentsToAcquireIntangibleAssets
    2.4.1.2.              ProceedsFromSaleOfIntangibleAssets
    2.4.2.           Loans and Advances
    2.4.2.1.               ProceedsFromRepaymentsOfLoansAndAdvancesToOtherEntities
    2.4.2.2.               PaymentsForLoansAndAdvancesToOtherEntities
    2.4.3.           Joint Ventures
    2.4.3.1.               PaymentsToAcquireJointVenture

    3.    NetCashProvidedByUsedInFinancingActivities
    3.1.        Equity Transactions
    3.1.1.            ProceedsFromIssuanceOfCommonStock
    3.1.2.            ProceedsFromIssuanceOfPreferredStock
    3.1.3.            ProceedsFromStockOptionsExercised
    3.1.4.            PaymentsForRepurchaseOfCommonStock
    3.1.5.            PaymentsForRepurchaseOfPreferredStock
    3.1.6.            ProceedsFromIssuanceOfOtherEquityInstruments
    3.1.7.            PaymentsForRepurchaseOfOtherEquityInstruments
    3.1.8.            ProceedsFromSaleOfTreasuryStock
    3.1.9.            PaymentsToAcquireTreasuryStock
    3.2.      Debt Transactions
    3.2.1.          ProceedsFromIssuanceOfDebt
    3.2.2.          RepaymentsOfDebt
    3.2.3.          ProceedsFromBorrowings
    3.2.4.          RepaymentsOfBorrowings
    3.3.       Dividends
    3.3.1.           DividendsPaid
    3.3.1.1.               DividendsPaidToNoncontrollingInterest
    3.3.1.2.               DividendsPaidToControllingInterest
    3.4.       Leases
    3.4.1.           PaymentsOfFinanceLeaseObligations
    3.4.2.           PaymentsOfOperatingLeaseLiabilities
    3.5.        Grants and Other Financing Sources
    3.5.1.            ProceedsFromGovernmentGrants

    4.    NetIncreaseDecreaseInCashAndCashEquivalents
    4.1.        CashAndCashEquivalentsPeriodIncreaseDecrease
    4.2.        EffectOfExchangeRateOnCashAndCashEquivalents
    4.3.        CashAndCashEquivalentsAtCarryingValue
    4.4.        CashAndCashEquivalentsBeginningOfPeriod

    </pre>




    Detailled View:
    <pre>
      Main Rules

      Post Rule (Cleanup)

    </pre>
    """
    prepivot_rule_tree = RuleGroup(
        prefix="CF_PREPIV",
        rules=[PrePivotDeduplicate(),]
    )

    cf_netcash_exrate = RuleGroup(
        prefix="NETCASH_ExRATE",
        rules=[
            # Continuing Op
            # -------------
            CopyTagRule(original='NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
                        target='NetCashProvidedByUsedInOperatingActivities'),
            CopyTagRule(original='NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
                        target='NetCashProvidedByUsedInInvestingActivities'),
            CopyTagRule(original='NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
                        target='NetCashProvidedByUsedInFinancingActivities'),

            # Continuing Op EffectsOnExRate
            CopyTagRule(original='EffectOfExchangeRateOnCashContinuingOperations',
                        target='EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations'),

            # Continuing Op NetCashProvided
            SumUpRule(sum_tag='NetCashProvidedByUsedInContinuingOperations',
                      potential_summands=[
                          'NetCashProvidedByUsedInOperatingActivities',
                          'NetCashProvidedByUsedInInvestingActivities',
                          'NetCashProvidedByUsedInFinancingActivities',
                          'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations'
                      ]),

            # Discontinued Op
            # -------------
            # Discontinued Op EffectsOnExRate
            CopyTagRule(original='EffectOfExchangeRateOnCashDiscontinuedOperations',
                        target='EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations'),

            # Discontinued Op NetCashProvided
            SumUpRule(sum_tag='NetCashProvidedByUsedInDiscontinuedOperations',
                      potential_summands=[
                          'CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations',
                          'CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations',
                          'CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations',
                          'EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations'
                      ]),

            # ExRateEffect
            # ----------------------
            CopyTagRule(original='EffectOfExchangeRateOnCash',
                        target='EffectOfExchangeRateOnCashAndCashEquivalents'),
            CopyTagRule(original='EffectOfExchangeRateOnCashAndCashEquivalents',
                        target='EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'),
            SumUpRule(sum_tag='EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
                      potential_summands=[
                          'EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
                          'EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsDisposalGroupIncludingDiscontinuedOperations'
                      ]),

            # Simplify name to EffectOfExchangeRateFinal
            CopyTagRule(original='EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations',
                        target='EffectOfExchangeRateFinal')

        ]
    )

    cf_increase_decrease = RuleGroup(
        prefix="INC_DEC",
        rules=[
            # Cash increase decrease Including ExRate Effect
            # ----------------------------------------------
            CopyTagRule(original='CashPeriodIncreaseDecrease',
                        target='CashAndCashEquivalentsPeriodIncreaseDecrease'),
            CopyTagRule(original='CashAndCashEquivalentsPeriodIncreaseDecrease',
                        target='CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect'),

            # Simplify name to CashTotalPeriodIncreaseDecreaseIncludingExRateEffect
            CopyTagRule(original='CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect',
                        target='CashTotalPeriodIncreaseDecreaseIncludingExRateEffect'),

            # Cash increase decrease Excluding ExRate Effect
            # ----------------------------------------------
            CopyTagRule(original='CashPeriodIncreaseDecreaseExcludingExchangeRateEffect',
                        target='CashAndCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect'),
            CopyTagRule(original='CashAndCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect',
                        target='CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect'),

            # Simplify name to CashTotalPeriodIncreaseDecreaseExcludingExRateEffect
            CopyTagRule(original='CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect',
                        target='CashTotalPeriodIncreaseDecreaseExcludingExRateEffect'),


        ])




        # todo: hier könnten noch missing summand/total rules definiert werden
        # für operating und discontinued
        # auch für CashTotalPeriodIncreaseDecreaseExcludingExRateEffect


    main_rule_tree = RuleGroup(prefix="CF",
                               rules=[
                                   cf_netcash_exrate,
                                   cf_increase_decrease,
                               ])

    preprocess_rule_tree = RuleGroup(prefix="CF_PRE",
                                     rules=[
                                     ])

    post_rule_tree = RuleGroup(
        prefix="CF",
        rules=[
            PostSetToZero(tags=['NetCashProvidedByUsedInOperatingActivities', ]),
            PostSetToZero(tags=['NetCashProvidedByUsedInInvestingActivities', ]),
            PostSetToZero(tags=['NetCashProvidedByUsedInFinancingActivities', ]),
            PostSetToZero(tags=['EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations', ]),
            PostSetToZero(tags=['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations', ]),
            PostSetToZero(tags=['CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations', ]),
            PostSetToZero(tags=['CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations', ]),
            PostSetToZero(tags=['EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations']),
            PostSetToZero(tags=['NetCashProvidedByUsedInDiscontinuedOperations']),
            PostSetToZero(tags=['EffectOfExchangeRateFinal']),

            MissingSumRule(sum_tag='NetCashProvidedByUsedInContinuingOperations',
                           summand_tags=['NetCashProvidedByUsedInOperatingActivities',
                                         'NetCashProvidedByUsedInInvestingActivities',
                                         'NetCashProvidedByUsedInFinancingActivities',
                                         'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations']),

            MissingSumRule(sum_tag='NetCashProvidedByUsedInDiscontinuedOperations',
                           summand_tags=['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations',
                                         'CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations',
                                         'CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations',
                                         'EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations']),

            MissingSumRule(sum_tag='CashTotalPeriodIncreaseDecreaseIncludingExRateEffect',
                           summand_tags=['CashTotalPeriodIncreaseDecreaseExcludingExRateEffect',
                                         'EffectOfExchangeRateFinal']),

            MissingSumRule(sum_tag='CashTotalPeriodIncreaseDecreaseIncludingExRateEffect',
                           summand_tags=['NetCashProvidedByUsedInContinuingOperations',
                                         'NetCashProvidedByUsedInDiscontinuedOperations',
                                         'EffectOfExchangeRateFinal']),




            # todo: hier werden noch final SUM up benötigt, für
            #  NetCashProvidedByUsedInContinuingOperations und NetCashProvidedByUsedInDiscontinuedOperations


        ])

    validation_rules: List[ValidationRule] = [
        SumValidationRule(identifier="NetCashContOp",
                          sum_tag='NetCashProvidedByUsedInContinuingOperations',
                          summands=['NetCashProvidedByUsedInOperatingActivities',
                                    'NetCashProvidedByUsedInFinancingActivities',
                                    'NetCashProvidedByUsedInInvestingActivities',
                                    'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations']),
        SumValidationRule(identifier="NetCashDiscontOp",
                          sum_tag='NetCashProvidedByUsedInDiscontinuedOperations',
                          summands=['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations',
                                    'CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations',
                                    'CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations',
                                    'EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations']),
        SumValidationRule(identifier="CashIncDecTotal",
                          sum_tag='CashTotalPeriodIncreaseDecreaseIncludingExRateEffect',
                          summands=['NetCashProvidedByUsedInContinuingOperations',
                                    'NetCashProvidedByUsedInDiscontinuedOperations',
                                    'EffectOfExchangeRateFinal']),
    ]

    # these are the columns that finally are returned after the standardization
    final_tags: List[str] = [
        'NetCashProvidedByUsedInOperatingActivities',
        'NetCashProvidedByUsedInFinancingActivities',
        'NetCashProvidedByUsedInInvestingActivities',
        'EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations',
        'NetCashProvidedByUsedInContinuingOperations',
        'CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations',
        'CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations',
        'CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations',
        'EffectOfExchangeRateOnCashAndCashEquivalentsDiscontinuedOperations',
        'NetCashProvidedByUsedInDiscontinuedOperations',
        'CashTotalPeriodIncreaseDecreaseExcludingExRateEffect',
        'EffectOfExchangeRateFinal',
        'CashTotalPeriodIncreaseDecreaseIncludingExRateEffect'
    ]

    # used to evaluate if a report is the main cashflow report
    # inside a report, there can be several tables (different report nr)
    # which stmt value is CF.
    # however, we might be only interested in the "major" CF report. Usually this is the
    # one which has the least nan in the following columns
    main_statement_tags = [
        'NetCashProvidedByUsedInOperatingActivities',
        'NetCashProvidedByUsedInFinancingActivities',
        'NetCashProvidedByUsedInInvestingActivities',
        'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInInvestingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInFinancingActivitiesContinuingOperations',
        'NetCashProvidedByUsedInContinuingOperations',
        'NetCashProvidedByUsedInDiscontinuedOperations',
        'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect',
        'CashAndCashEquivalentsPeriodIncreaseDecrease',
        'CashPeriodIncreaseDecrease',
    ]

    def __init__(self, filter_for_main_statement: bool = True, iterations: int = 3):
        super().__init__(
            prepivot_rule_tree=self.prepivot_rule_tree,
            pre_rule_tree=self.preprocess_rule_tree,
            main_rule_tree=self.main_rule_tree,
            post_rule_tree=self.post_rule_tree,
            validation_rules=self.validation_rules,
            final_tags=self.final_tags,
            main_iterations=iterations,
            filter_for_main_statement=filter_for_main_statement,
            main_statement_tags=self.main_statement_tags)
