CREATE TABLE `Ortholog_Pair_Best` (
  `opb_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `species1` int(11) NOT NULL DEFAULT '0',
  `geneid1` int(11) NOT NULL DEFAULT '0',
  `species2` int(11) NOT NULL DEFAULT '0',
  `geneid2` bigint(20) NOT NULL DEFAULT '0',
  `score` int(11) DEFAULT NULL,
  `best_score` enum('Yes','No','Yes_Adjusted') CHARACTER SET utf8 DEFAULT NULL,
  `best_score_rev` enum('Yes','No') CHARACTER SET utf8 DEFAULT NULL,
  `confidence` enum('high','low','moderate') CHARACTER SET utf8 DEFAULT NULL,
  `max(score)` int(11) DEFAULT NULL,
  `if_align` tinyint(1) DEFAULT '0',
  `ortholog_score` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`opb_id`),
  KEY `geneid1` (`geneid1`),
  KEY `geneid2` (`geneid2`),
  KEY `species1` (`species1`,`geneid1`,`species2`,`geneid2`)
) ENGINE=InnoDB AUTO_INCREMENT=33060977 DEFAULT CHARSET=latin1;
