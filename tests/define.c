
volatile char x = 20 + 20;
void main(){
    char a;
    char c = 10+a;
    volatile char b = x + c;
    if(b > 50){
        a = b - 5;
    }
}