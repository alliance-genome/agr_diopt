CREATE TABLE `Ortholog_Max_Score` (
  `species1` int(11) NOT NULL DEFAULT '0',
  `species2` int(11) NOT NULL DEFAULT '0',
  `common_name` varchar(64) DEFAULT NULL,
  `species_name` varchar(128) DEFAULT NULL,
  `max_score` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
