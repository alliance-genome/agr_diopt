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
) ENGINE=InnoDB AUTO_INCREMENT=16583983 DEFAULT CHARSET=utf8;
