String trame_historique(char *etiquette, char *donnee ){

  String trame="";
  String information="";


  information =   etiquette;
  information +=  char(0x20);
  information +=  donnee;


  int lengh = information.length();

  char checksum=0;
  for (int i=0; i<lengh; i++)  
     { 
      checksum = checksum + char(information[i]);
     }
   checksum = (checksum & 0x3F) + 0x20;
   trame=char(0x0A);
   trame+=information;
   trame+=char(0x20);
   trame+=char(checksum);
   trame+=char(0x0D);

   return trame;
}
