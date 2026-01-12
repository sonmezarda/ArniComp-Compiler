int main(){
   volatile char a = 50;
   volatile char b;
   if(a > 50){
       b = 100;
   } else {
       b = 200;
   }
}