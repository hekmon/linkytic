int i=0;


void setup() {
Serial.begin(1200,SERIAL_7E1);
//Serial.begin(9600);

}

void loop() {

 
  if (i==20){
    
      Serial.print(trame_historique("ADCO", "123456789012"));
      delay(13);
      Serial.print(trame_historique("OPTARIF", "BASE"));
      delay(13);
      Serial.print(trame_historique("ISOUSC", "60"));
      delay(13);
      Serial.print(trame_historique("BASE", "000015000"));
      delay(13);
      Serial.print(trame_historique("PETC", "TH12"));
      delay(13);
      Serial.print(trame_historique("IINST1", "012"));
      delay(13);
      Serial.print(trame_historique("IINST2", "014"));
      delay(13);
      Serial.print(trame_historique("IINST3", "013"));
      delay(13);
      Serial.print(trame_historique("IMAX1", "060"));
      delay(13);
      Serial.print(trame_historique("IMAX2", "060"));  
      delay(13);
      Serial.print(trame_historique("IMAX3", "060"));
      delay(13);
      Serial.print(trame_historique("PMAX", "09000"));
      delay(13);
      Serial.print(trame_historique("PAPP", "00700"));
      delay(13);
      Serial.print(trame_historique("HHPHC", "A"));
      delay(13);
      Serial.print(trame_historique("MOTDETAE", "000000"));
      delay(13);
      Serial.print(trame_historique("PPOT", "00"));
      i=0;
    }

      delay(33);    
 Serial.print(trame_historique("ADIR1", "005"));
      delay(13); 
 Serial.print(trame_historique("ADIR2", "003"));
      delay(13);
 Serial.print(trame_historique("ADIR3", "004"));
      delay(13);
 Serial.print(trame_historique("ADCO", "123456789012"));
      delay(13);
 Serial.print(trame_historique("IINST1", "034"));
      delay(13);
 Serial.print(trame_historique("IINST2", "028"));
      delay(13); 
 Serial.print(trame_historique("IINST3", "053")); 

  

  
 delay(33);

}
