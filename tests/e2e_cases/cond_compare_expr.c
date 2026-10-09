int main() {
    volatile char a = 7;
    volatile char b = 5;
    volatile char gt = 0;
    volatile char le = 0;
    volatile char eq = 0;
    volatile char ne = 0;

    gt = a > b;
    le = a <= b;
    eq = a == 7;
    ne = a != b;
}
