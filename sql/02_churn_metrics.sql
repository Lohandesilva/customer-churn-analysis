-- Metric definitions. One place where each KPI is defined, so the dashboard,
-- the Python pipeline and any ad-hoc query all agree on what "churn rate" means.

-- ---------------------------------------------------------------------------
-- Portfolio position: accounts, revenue, and the gap between the two.
-- The account-share / revenue-share gap is the headline of the whole analysis,
-- so it gets its own line rather than being derived downstream.
-- ---------------------------------------------------------------------------
create or replace view vw_portfolio_position as
select
    count(*)                                                    as accounts,
    sum(monthly_charges)                                        as mrr,
    sum(monthly_charges) * 12                                   as arr,
    sum(is_churned)                                             as churned_accounts,
    avg(is_churned)                                             as churn_rate_accounts,
    sum(monthly_charges) filter (where is_churned = 1)          as mrr_lost,
    sum(monthly_charges) filter (where is_churned = 1) * 12      as arr_lost,
    sum(monthly_charges) filter (where is_churned = 1)
        / nullif(sum(monthly_charges), 0)                       as churn_rate_revenue,
    avg(monthly_charges) filter (where is_churned = 1)          as avg_bill_leaver,
    avg(monthly_charges) filter (where is_churned = 0)          as avg_bill_stayer
from stg_customers;

-- ---------------------------------------------------------------------------
-- Segment view. Ordered by revenue lost rather than churn rate, because a high
-- churn rate on a small segment is not where the money is.
-- ---------------------------------------------------------------------------
create or replace view vw_segment_performance as
with base as (
    select
        contract_type,
        internet_service,
        count(*)                                            as accounts,
        sum(is_churned)                                     as churned_accounts,
        avg(is_churned)                                     as churn_rate,
        sum(monthly_charges)                                as mrr,
        sum(monthly_charges) filter (where is_churned = 1)  as mrr_lost,
        avg(monthly_charges)                                as avg_bill,
        avg(tenure_months)                                  as avg_tenure,
        avg(addon_count)                                    as avg_addons
    from stg_customers
    group by contract_type, internet_service
)
select
    b.*,
    mrr_lost / nullif(sum(mrr_lost) over (), 0)  as share_of_total_loss,
    sum(mrr_lost) over (order by mrr_lost desc)
        / nullif(sum(mrr_lost) over (), 0)       as cumulative_share_of_loss
from base b
order by mrr_lost desc;

-- ---------------------------------------------------------------------------
-- Discrete-time hazard by tenure month.
-- At-risk population at month t is everyone whose tenure reached t, which is a
-- self-join on the tenure grid rather than a simple group-by. This is the SQL
-- equivalent of the product-limit estimator in src/survival.py.
-- ---------------------------------------------------------------------------
create or replace view vw_tenure_hazard as
with grid as (
    select distinct tenure_months as t from stg_customers
),
counts as (
    select
        g.t,
        (select count(*) from stg_customers c where c.tenure_months >= g.t)      as at_risk,
        (select count(*) from stg_customers c
          where c.tenure_months = g.t and c.is_churned = 1)                      as events
    from grid g
)
select
    t                                    as tenure_month,
    at_risk,
    events,
    events::numeric / nullif(at_risk, 0) as hazard,
    exp(sum(ln(1 - events::numeric / nullif(at_risk, 0)))
        over (order by t rows between unbounded preceding and current row))
                                         as survival
from counts
where at_risk > 0 and events < at_risk
order by t;

-- ---------------------------------------------------------------------------
-- Revenue concentration. Answers "how much of the loss sits in how few
-- segments" without hard-coding a segment list.
-- ---------------------------------------------------------------------------
create or replace view vw_loss_concentration as
select
    contract_type || ' / ' || internet_service           as segment,
    mrr_lost,
    share_of_total_loss,
    cumulative_share_of_loss,
    row_number() over (order by mrr_lost desc)          as rank_by_loss
from vw_segment_performance
where mrr_lost > 0
order by mrr_lost desc;

-- ---------------------------------------------------------------------------
-- Attachment effect. Add-on products are sold as an ARPU lever; this checks
-- whether they are also a retention lever, before the model is consulted.
-- ---------------------------------------------------------------------------
create or replace view vw_attachment_effect as
select
    addon_count,
    count(*)                as accounts,
    avg(is_churned)         as churn_rate,
    avg(monthly_charges)    as avg_bill,
    avg(tenure_months)      as avg_tenure,
    avg(is_churned) - (select avg(is_churned) from stg_customers) as vs_base_rate
from stg_customers
group by addon_count
order by addon_count;
