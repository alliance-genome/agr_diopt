CREATE TABLE `Ortholog_Pair` (
  `ortholog_pairid` int(11) NOT NULL AUTO_INCREMENT,
  `speciesid1` int(11) DEFAULT NULL,
  `geneid1` int(11) DEFAULT NULL,
  `speciesid2` int(11) DEFAULT NULL,
  `geneid2` int(11) DEFAULT NULL,
  `prediction_method` varchar(50) DEFAULT NULL,
  `blast_score` varchar(100) DEFAULT NULL,
  `orig_score` varchar(100) DEFAULT NULL,
  `orig_score_info` varchar(100) DEFAULT NULL,
  `orig_clusterid` varchar(100) DEFAULT NULL,
  `url` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`ortholog_pairid`),
  KEY `OP_speciesgene1` (`speciesid1`,`geneid1`),
  KEY `OP_geneid1` (`geneid1`),
  KEY `speciesid2` (`speciesid2`),
  KEY `speciesid1` (`speciesid1`)
) ENGINE=InnoDB AUTO_INCREMENT=63610841 DEFAULT CHARSET=latin1;
