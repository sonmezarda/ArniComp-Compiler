int main(){
    char a = 50;
    volatile char b = a;
    a = 100;
    b = a;
}