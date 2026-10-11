-- SYNTHETIC scientific edge cases; these rows are not DRSC results.
CREATE TABLE `Species` (
  `speciesid` int(11) NOT NULL DEFAULT '0',
  `species_name` varchar(128) DEFAULT NULL,
  `short_species_name` varchar(5) DEFAULT NULL,
  `common_name` varchar(64) DEFAULT NULL,
  `species_specific_geneid_type` varchar(100) DEFAULT NULL,
  `species_specific_database_URL` varchar(255) DEFAULT NULL,
  `species_specific_URL_format` varchar(255) DEFAULT NULL,
  `display_order` int(11) DEFAULT NULL,
  `test_2` int(11) DEFAULT NULL,
  PRIMARY KEY (`speciesid`),
  KEY `species_name` (`species_name`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

CREATE TABLE `Gene_Information` (
  `geneid` int(11) NOT NULL,
  `speciesid` int(11) DEFAULT NULL,
  `symbol` varchar(33) CHARACTER SET latin1 DEFAULT NULL,
  `symbol_cs` varchar(33) CHARACTER SET latin1 COLLATE latin1_bin DEFAULT NULL,
  `description` text CHARACTER SET latin1,
  `locus_tag` varchar(50) CHARACTER SET latin1 DEFAULT NULL,
  `species_specific_geneid` varchar(100) CHARACTER SET latin1 DEFAULT NULL,
  `species_specific_geneid_type` varchar(100) CHARACTER SET latin1 DEFAULT NULL,
  `chromosome` varchar(50) CHARACTER SET latin1 DEFAULT NULL,
  `map_location` varchar(50) CHARACTER SET latin1 DEFAULT NULL,
  `gene_type` varchar(50) CHARACTER SET latin1 DEFAULT NULL,
  `ensembl_geneid` varchar(50) CHARACTER SET latin1 DEFAULT NULL,
  PRIMARY KEY (`geneid`),
  KEY `symbol` (`symbol`),
  KEY `species_symbol` (`speciesid`,`symbol`),
  KEY `species` (`speciesid`),
  KEY `species_specific_geneid` (`species_specific_geneid`),
  KEY `symbol_cs` (`symbol_cs`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `GeneID_Mapping` (
  `genemappingid` int(11) NOT NULL AUTO_INCREMENT,
  `speciesid` int(11) DEFAULT NULL,
  `geneid` int(11) DEFAULT NULL,
  `idtype` varchar(50) DEFAULT NULL,
  `idvalue` varchar(512) DEFAULT '' COMMENT 'Not Case Sensitive',
  `idvalue2` varchar(512) DEFAULT NULL COMMENT 'Case Sensitive',
  `extra_info` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`genemappingid`),
  KEY `GIM_typevalue` (`idtype`,`idvalue`(128)),
  KEY `GIM_idvalue` (`idvalue`(128)),
  KEY `geneid` (`geneid`),
  KEY `idvalue2` (`idvalue2`(255))
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

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
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

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
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;

CREATE TABLE `Prediction_Method` (
  `prediction_method` varchar(64) NOT NULL,
  `method_label` varchar(64) DEFAULT ' ',
  `source` varchar(128) DEFAULT NULL,
  `description` text,
  `URL` varchar(256) DEFAULT NULL,
  `version` varchar(64) DEFAULT NULL,
  `release_date` date DEFAULT NULL,
  `date_downloaded` date DEFAULT NULL,
  `type` varchar(16) DEFAULT NULL,
  `year_published` int(11) DEFAULT NULL,
  `institute` varchar(256) DEFAULT NULL,
  `algorithms` text,
  `coverage` varchar(128) DEFAULT NULL,
  `PMID` int(11) DEFAULT NULL,
  `reference` text,
  `color` char(6) DEFAULT NULL,
  `weight` float DEFAULT NULL,
  PRIMARY KEY (`prediction_method`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

CREATE TABLE `Ortholog_Max_Score` (
  `species1` int(11) NOT NULL DEFAULT '0',
  `species2` int(11) NOT NULL DEFAULT '0',
  `common_name` varchar(64) DEFAULT NULL,
  `species_name` varchar(128) DEFAULT NULL,
  `max_score` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


INSERT INTO Species (speciesid,species_name,common_name) VALUES (7227,'Drosophila melanogaster','Fly'),(9606,'Homo sapiens','Human'),(10090,'Mus musculus','Mouse');
INSERT INTO Gene_Information (geneid,speciesid,symbol,species_specific_geneid) VALUES
 (101,7227,'ProbeA','FB-test-A'),(102,7227,'ProbeB','FB-test-B'),(103,7227,'NoPair','FB-test-C'),
 (201,9606,'TargetA','HGNC-test-A'),(202,9606,'TargetB','HGNC-test-B'),(203,9606,'TargetC','HGNC-test-C');
INSERT INTO GeneID_Mapping (speciesid,geneid,idtype,idvalue,idvalue2,extra_info) VALUES
 (7227,101,'Symbol','ProbeA','ProbeA','Entrez official symbol'),
 (7227,102,'Alias','ProbeA','probea','Entrez synonym'),
 (7227,101,'Alias','Shared','Shared','Entrez synonym'),
 (7227,102,'Alias','Shared','Shared','Entrez synonym'),
 (7227,103,'Symbol','NoPair','NoPair','Entrez official symbol'),
 (7227,101,'Stable ID','FB-test-A','FB-test-A','Stable ID');
INSERT INTO Ortholog_Pair_Best (species1,geneid1,species2,geneid2,score,best_score,best_score_rev,confidence,ortholog_score) VALUES
 (7227,101,9606,201,5,'Yes_Adjusted','No','high',4.25),
 (7227,101,9606,202,NULL,NULL,NULL,NULL,NULL),
 (10090,101,9606,203,99,'Yes','Yes','high',99.99);
INSERT INTO Ortholog_Pair (speciesid1,geneid1,speciesid2,geneid2,prediction_method) VALUES
 (7227,101,9606,201,'Method A'),(7227,101,9606,201,'Method A'),(7227,101,9606,201,'Method B'),
 (10090,101,9606,201,'Wrong species method');
INSERT INTO Gene_Information (geneid,speciesid,symbol) VALUES (104,7227,'Large'),(105,7227,'Conflict');
INSERT INTO GeneID_Mapping (speciesid,geneid,idvalue,idvalue2,extra_info) VALUES
 (7227,104,'Large','Large','Entrez official symbol'),(7227,105,'Conflict','Conflict','Entrez official symbol');
INSERT INTO Ortholog_Pair_Best (species1,geneid1,species2,geneid2,score,ortholog_score) VALUES
 (7227,104,9606,9007199254740993,1,1.01),(7227,105,9606,201,1,1.00),(7227,105,9606,201,2,2.00);

-- Confidence ordering: confidence takes precedence over vote count; nulls last.
INSERT INTO Gene_Information (geneid,speciesid,symbol) VALUES (106,7227,'Ranking');
INSERT INTO GeneID_Mapping (speciesid,geneid,idvalue,idvalue2,extra_info) VALUES
 (7227,106,'Ranking','Ranking','Entrez official symbol');
INSERT INTO Ortholog_Pair_Best (species1,geneid1,species2,geneid2,score,confidence) VALUES
 (7227,106,9606,211,99,'low'),(7227,106,9606,212,1,'high'),
 (7227,106,9606,213,9,'moderate'),(7227,106,9606,214,3,'high'),
 (7227,106,9606,215,100,NULL),(7227,106,9606,216,NULL,'high');

-- Species-pair maximum score. No reverse (9606 -> 7227) row: tests the null case.
INSERT INTO Ortholog_Max_Score (species1,species2,common_name,species_name,max_score) VALUES
 (7227,9606,'Human','Homo sapiens',5);
