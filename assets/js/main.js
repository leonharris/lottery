// maybe there's a better way of doing this???
// check wildlife photographer site



// save previous lotto results to sessionStorage
//localStorage.setItem('lotto_results', JSON.stringify(lotto_data));
//let winning_numbers = JSON.parse(localStorage.getItem('lotto_results'));
//console.log(winning_numbers);

/*
// Create div with last draws winning numbers
function latest_lotto_draw(lotto_data) {
	let draw_result_div = document.getElementById('latest-draw-result');
	let draw_result = lotto_data[2066]['draw_result'];
	draw_result_div.insertAdjacentHTML("beforeend", '<p>Latest result</p>');
	draw_result_div.append(draw_result);
}
latest_lotto_draw(lotto_data);
*/

const lotto_grid = document.getElementById("lotto");
const btn_spin_lotto = document.getElementById('btn_spin_lotto');

/* sort toggle */
let sort_val = document.getElementById("sort-toggle-switch").checked ? true : false;
document.getElementById("sort-toggle-switch").addEventListener('change', sortChange);
function sortChange(){
	sort_val = this.checked ? true : false;
}

/* draw type toggle */
let draw_type = document.getElementById("draw-type-toggle-switch").checked ? 'euromillions' : 'lotto';
document.getElementById("draw-type-toggle-switch").addEventListener('change', drawTypeChange);
function drawTypeChange(){
	reset_balls();
	draw_type = this.checked ? 'euromillions' : 'lotto';
	lotto_grid.setAttribute('data-draw-type', draw_type);

}

// clear the grid of balls
function reset_balls() {

	// check if circle element exists, and delete it if it does
	// prevent duplicate lotto number circles from popping up
	if (document.getElementsByClassName('ball').length) {
		const removeElements = (elms) => elms.forEach(el => el.remove());
		removeElements( document.querySelectorAll(".ball") );
	}

}

// Spin the balls
btn_spin_lotto.addEventListener("click", function(e) {

	reset_balls();

	if (draw_type == 'lotto') {
		generateNumbers(6, 59, sort_val);
	} else {
		generateNumbers(5, 50, sort_val);
		generateNumbers(2, 12, sort_val); // generate bonus balls
	}

});

function generateNumbers(quantity, max_number, sort) {

	let arr = [];
	while(arr.length < quantity){
		let r = Math.floor(Math.random() * max_number) + 1;
		if(arr.indexOf(r) === -1) arr.push(r);
		let add = true;

		// looks for duplicate numbers
		// if duplicate exists it does not add it to the array
		for(let y = 0; y < max_number; y++) {
			if(arr[y] == arr) {
				add = false;
			}
		}

	}

	// for each element of array it adds it creates an element
	// and adds the class circle to each each
	// and then appends it to the lotto element

	if (sort == true) {

		//sorts array by ascending order and adds it into new array
		const sorted = [...arr].sort((a,b)=>a-b);

		sorted.forEach(function (number) {
			let ball = document.createElement('div');
			let number_wrap = document.createElement('span');
			let number_range = 'range-' + (Math.ceil((number / 10) + 0.01));
			let ball_class = 'ball';
			ball.setAttribute('class', ball_class);
			ball.setAttribute('data-range', number_range);
			number_wrap.setAttribute('class', 'number');
			number_wrap.textContent = number;
			ball.append(number_wrap);
			lotto_grid.append(ball);
		});

	} else {

		arr.forEach(function (number) {
			let ball = document.createElement('div');
			let number_wrap = document.createElement('span');
			let number_range = 'range-' + (Math.ceil((number / 10) + 0.01));
			let ball_class = 'ball';
			ball.setAttribute('class', ball_class);
			ball.setAttribute('data-range', number_range);
			number_wrap.setAttribute('class', 'number');
			number_wrap.textContent = number;
			ball.append(number_wrap);
			lotto_grid.append(ball);
		});

	}

}
