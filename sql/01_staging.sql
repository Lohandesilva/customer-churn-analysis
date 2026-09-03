-- Staging model for the churn analysis.
-- PostgreSQL. Loads the raw extract as text, then casts and applies the same
-- cleaning rules as src/ingest.py so the SQL and Python paths agree.

drop table if exists stg_customers cascade;

create table stg_customers as
with raw as (
    select
        "customerID"                                as customer_id,
        nullif(trim("TotalCharges"), '')            as total_charges_txt,
        cast("MonthlyCharges" as numeric(10, 2))    as monthly_charges,
        cast("tenure" as integer)                   as tenure_months,
        "Contract"                                  as contract_type,
        "InternetService"                           as internet_service,
        "PaymentMethod"                             as payment_method,
        "PaperlessBilling"                          as paperless_billing,
        "Partner"                                   as has_partner,
        "Dependents"                                as has_dependents,
        cast("SeniorCitizen" as integer)            as is_senior,
        "PhoneService"                              as phone_service,
        "MultipleLines"                             as multiple_lines,
        "OnlineSecurity"                            as online_security,
        "OnlineBackup"                              as online_backup,
        "DeviceProtection"                          as device_protection,
        "TechSupport"                               as tech_support,
        "StreamingTV"                               as streaming_tv,
        "StreamingMovies"                           as streaming_movies,
        "Churn"                                     as churn_flag
    from raw_telco_churn
),

-- "No internet service" and "No phone service" describe the same state as "No".
-- Collapsing them here keeps every downstream count consistent with the Python
-- pipeline and stops the same customer being classified two ways.
normalised as (
    select
        customer_id,
        monthly_charges,
        tenure_months,
        contract_type,
        internet_service,
        payment_method,
        is_senior,
        -- Unbilled tenure-zero accounts carry a blank; the true value is zero.
        coalesce(cast(total_charges_txt as numeric(12, 2)), 0) as total_charges,
        case when churn_flag = 'Yes' then 1 else 0 end          as is_churned,
        case when paperless_billing = 'Yes' then 1 else 0 end   as is_paperless,
        case when has_partner = 'Yes' then 1 else 0 end         as has_partner,
        case when has_dependents = 'Yes' then 1 else 0 end      as has_dependents,
        case when multiple_lines   = 'Yes' then 1 else 0 end    as multiple_lines,
        case when online_security  = 'Yes' then 1 else 0 end    as online_security,
        case when online_backup    = 'Yes' then 1 else 0 end    as online_backup,
        case when device_protection = 'Yes' then 1 else 0 end   as device_protection,
        case when tech_support     = 'Yes' then 1 else 0 end    as tech_support,
        case when streaming_tv     = 'Yes' then 1 else 0 end    as streaming_tv,
        case when streaming_movies = 'Yes' then 1 else 0 end    as streaming_movies
    from raw
)

select
    n.*,
    (online_security + online_backup + device_protection
     + tech_support + streaming_tv + streaming_movies)          as addon_count,
    case when payment_method like '%automatic%' then 1 else 0 end as is_autopay,
    case when internet_service = 'Fiber optic' then 1 else 0 end  as is_fibre,
    case when contract_type = 'Month-to-month' then 1 else 0 end  as is_month_to_month,
    case
        when tenure_months <  6 then '0-6m'
        when tenure_months < 12 then '6-12m'
        when tenure_months < 24 then '12-24m'
        when tenure_months < 48 then '24-48m'
        when tenure_months < 72 then '48-72m'
        else '72m+'
    end                                                           as tenure_band,
    -- Revenue actually realised per month of tenure diverges from the current
    -- bill whenever a customer has changed plan, so both are kept.
    case when tenure_months > 0
         then round(total_charges / tenure_months, 2)
         else monthly_charges
    end                                                           as arpu_realised
from normalised n;

create index on stg_customers (contract_type, internet_service);
create index on stg_customers (is_churned);

-- Assertions. These should return zero rows; if they do not, the source changed.
-- Blank TotalCharges must only ever appear on tenure-zero accounts.
select 'blank_total_charges_on_tenured_account' as check_name, count(*) as failures
from stg_customers where total_charges = 0 and tenure_months > 0
union all
select 'duplicate_customer_id', count(*) - count(distinct customer_id) from stg_customers
union all
select 'negative_monthly_charges', count(*) from stg_customers where monthly_charges < 0;
