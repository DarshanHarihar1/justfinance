-- Phase 7: analytics base view (reviewed, categorized, non-excluded spending)
CREATE OR REPLACE VIEW v_spend AS
SELECT
    t.id,
    t.date,
    t.amount,
    t.type,
    t.category_id,
    t.merchant_normalized,
    t.statement_id,
    c.name AS category_name,
    c.color AS category_color
FROM transactions t
JOIN categories c ON c.id = t.category_id
WHERE t.needs_review = FALSE
  AND c.excluded_from_spending = FALSE
  AND t.category_id IS NOT NULL;
