int main() {
    volatile char src = 1;
    volatile char src0 = 0;
    volatile char bit = 0;
    volatile char neg = 0;
    volatile char not1 = 0;
    volatile char not0 = 0;

    bit = ~src;
    neg = -src;
    not1 = !src;
    not0 = !src0;
}
