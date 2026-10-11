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
