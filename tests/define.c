
char x = 20 + 20;
void main(){
    volatile char a;
    char c = 10;
    volatile char b = x + c;
    if(b > 50){
        a = b - 5;
    }
    b = 20;
}