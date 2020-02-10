SELECT create_schema_if_not_exist('gestion');

CREATE OR REPLACE VIEW gestion.a_v_infrastructure AS (
	SELECT e.geom, t.*
	FROM a_t_infrastructure AS t, a_b_infrastructure AS b, e_t_evenement AS e
	WHERE t.evenement = e.id AND t.type = b.id
);

