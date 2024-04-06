import time
from typing import List

import pandas as pd

from secfsdstools.d_container.databagmodel import JoinedDataBag
from secfsdstools.e_collector.companycollecting import CompanyReportCollector
from secfsdstools.e_filter.joinedfiltering import FilterBase, AdshJoinedFilter
from secfsdstools.e_filter.rawfiltering import ReportPeriodRawFilter, MainCoregRawFilter, \
    OfficialTagsOnlyRawFilter, USDOnlyRawFilter
from secfsdstools.f_standardize.is_standardize import IncomeStatementStandardizer
from secfsdstools.f_standardize.standardizing import StandardizedBag


def timing(f):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        print('{:s} function took {:.3f} ms'.format(f.__name__, (time2 - time1) * 1000.0))

        return ret

    return wrap


def prepare_all_data_set():
    bag = JoinedDataBag.load("../notebooks/set/parallel/IS/joined")
    bag = bag[ISQrtrsFilter()]
    bag.save("../notebooks/set/filtered/IS/joined")


@timing
def load_joined_IS_set() -> JoinedDataBag:
    return JoinedDataBag.load("../notebooks/set/filtered/IS/joined")


@timing
def create_smaller_sample_IS_set():
    bag = CompanyReportCollector.get_company_collector(ciks=[789019, 1652044, 1018724],
                                                       stmt_filter=[
                                                           'IS']).collect()  # Microsoft, Alphabet, Amazon
    filtered_bag = bag[ReportPeriodRawFilter()][MainCoregRawFilter()][OfficialTagsOnlyRawFilter()][
        USDOnlyRawFilter()]
    filtered_bag.join()[ISQrtrsFilter()].save("./saved_data/is_small_joined")


@timing
def load_smaller_sample_IS_set() -> JoinedDataBag:
    return JoinedDataBag.load("./saved_data/is_small_joined")


def filter_tags(pre_num_df: pd.DataFrame, tag_like: str) -> List[str]:
    return [x for x in pre_num_df.tag.unique().tolist() if tag_like in x]


def find_entries_with_all_tags(bag: JoinedDataBag, tag_list: List[str]):
    filtered_tags_df = bag.pre_num_df[bag.pre_num_df.tag.isin(tag_list)]
    filtered_df = filtered_tags_df[['adsh', 'tag']]
    counted_df = filtered_df.groupby(['adsh']).count()
    no_index = counted_df.reset_index()
    single_entry = no_index[no_index.tag==1].adsh.tolist()
    single_tags = filtered_df[filtered_df.adsh.isin(single_entry)]

    return counted_df[counted_df.tag == len(tag_list)].index.tolist()


@timing
def standardize(is_joined_bag: JoinedDataBag) -> StandardizedBag:
    is_standardizer = IncomeStatementStandardizer()
    is_joined_bag.present(is_standardizer)
    return is_standardizer.get_standardize_bag()


class ISQrtrsFilter(FilterBase):
    """
    Filters the data, so that only datapoints for 4 qtrs for 10-K,
    and 1 qtrs for 10-Q are kept.
    """

    def filter(self, bag: JoinedDataBag) -> JoinedDataBag:
        # Temporäres DataFrame für "form" hinzufügen
        temp_pre_num_df = pd.merge(bag.pre_num_df, bag.sub_df[['adsh', 'form']], on='adsh',
                                   how='inner')

        # Filterkriterien
        criteria = (
                ((temp_pre_num_df['form'] == '10-K') & (temp_pre_num_df['qtrs'] == 4)) |
                ((temp_pre_num_df['form'] == '10-Q') & (temp_pre_num_df['qtrs'] == 1))
        )

        # Ergebnis DataFrame B filtern
        pre_num_df = temp_pre_num_df[criteria]
        del pre_num_df['form']
        return JoinedDataBag.create(sub_df=bag.sub_df, pre_num_df=pre_num_df)


def check_signed_values(is_joined_bag: JoinedDataBag, tag_list: List[str]):

    just_cost = is_joined_bag.pre_num_df[['tag', 'value', 'negating']]
    just_cost = just_cost[just_cost.tag.isin(tag_list)]
    just_cost = just_cost[~(just_cost.value.isna() | (just_cost.value == 0.0))]
    just_cost['value_pos'] = just_cost.value >= 0.0
    return just_cost.groupby(['negating', 'value_neg']).count()


if __name__ == '__main__':
    # create_smaller_sample_IS_set()
    # prepare_all_data_set()

    is_joined_bag: JoinedDataBag = load_joined_IS_set()
    # print(check_signed_values(is_joined_bag, tag_list=['LicenseCost',
    #                                              'CostOfRevenue',
    #                                              'CostOfGoodsAndServicesSold',
    #                                              'CostOfGoodsSold',
    #                                              'CostOfServices']))

    # is_joined_bag = is_joined_bag.filter(AdshJoinedFilter(adshs=['0001193125-16-481920']))

    #is_joined_bag = load_smaller_sample_IS_set()
    #
    print(find_entries_with_all_tags(bag=is_joined_bag,
                               tag_list=[
                                   'RegulatedAndUnregulatedOperatingRevenue',
                                   'HealthCareOrganizationPatientServiceRevenue',
                                   'SalesRevenueGoodsGross',
                                   'ContractsRevenue',
                                   'RevenueOilAndGasServices',
                                   'HealthCareOrganizationRevenue',
                                   'RevenueMineralSales',
                                   'SalesRevenueEnergyServices',
                                   'RealEstateRevenueNet',
                                   'InterestAndDividendIncomeOperating',
                                   'InterestIncomeExpenseNet',
                                   'NoninterestIncome',
                                   'OperatingLeasesIncomeStatementLeaseRevenue',
                                   'LicensesRevenue', 'RevenueFromRelatedParties',
                                   'BrokerageCommissionsRevenue', 'RoyaltyRevenue', 'OilAndGasSalesRevenue',
                                   'OilAndGasRevenue', 'OtherRealEstateRevenue',
                                   'TechnologyServicesRevenue', 'ManagementFeesRevenue',
                                   'ReimbursementRevenue',
                                   'OperatingLeasesIncomeStatementMinimumLeaseRevenue',
                                   'FoodAndBeverageRevenue', 'MaintenanceRevenue',
                                   'LicenseAndServicesRevenue', 'FranchiseRevenue', 'SubscriptionRevenue',
                                   'FinancialServicesRevenue',
                                   'RevenueFromGrants',
                                   'GasGatheringTransportationMarketingAndProcessingRevenue',
                                   'OccupancyRevenue', 'NaturalGasProductionRevenue',
                                   'SalesRevenueServicesGross', 'InvestmentBankingRevenue',
                                   'AdvertisingRevenue', 'RevenueOtherFinancialServices',
                                   'OilAndCondensateRevenue', 'RevenueFromLeasedAndOwnedHotels',
                                   'RevenuesNetOfInterestExpense', 'RegulatedAndUnregulatedOperatingRevenue',
                                   'UnregulatedOperatingRevenue', 'ElectricUtilityRevenue',
                                   'CargoAndFreightRevenue', 'OtherHotelOperatingRevenue',
                                   'CasinoRevenue', 'RefiningAndMarketingRevenue',
                                   'PrincipalTransactionsRevenue', 'InterestRevenueExpenseNet',
                                   'HomeBuildingRevenue', 'OtherRevenueExpenseFromRealEstateOperations',
                                   'GasDomesticRegulatedRevenue', 'LicenseAndMaintenanceRevenue',
                                   'RegulatedOperatingRevenue', 'AdmissionsRevenue', 'PassengerRevenue'
                               ]))
    # print(filter_tags(is_joined_bag.pre_num_df, tag_like="SalesRevenue"))
    #
    # # check the loaded data
    print("sub_df", is_joined_bag.sub_df.shape)
    print("pre_num_df", is_joined_bag.pre_num_df.shape)

    standardized_bag = standardize(is_joined_bag)

    print(standardized_bag.result_df.shape)

    print("wait")
