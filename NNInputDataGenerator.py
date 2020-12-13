from SimAccount import SimAccount

class NNInputDataGenerator:
    def generate_nn_input_data_limit(self, divergence_scaled):
        #ma divergence
        input_data = np.array(divergence_scaled).T.tolist()

        if SimAccount.order_id != '':
            if SimAccount.order_side == 'buy':
                input_data.append(0)
                input_data.append(1)
                input_data.append(0)
            elif SimAccount.order_side == 'sell':
                input_data.append(0)
                input_data.append(0)
                input_data.append(1)
            else:
                print('Unknown order side! ', SimAccount.order_side)
                input_data.append(0)
                input_data.append(0)
                input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(0)
            input_data.append(0)

        if SimAccount.holding_side =='buy':
            input_data.append(0)
            input_data.append(1)
            input_data.append(0)
        elif SimAccount.holding_side =='sell':
            input_data.append(0)
            input_data.append(0)
            input_data.append(1)
        else:
            input_data.append(1)
            input_data.append(0)
            input_data.append(0)

        #//ac pl, 損益率を2unitにわけて表現する
        if SimAccount.unrealized_pl == 0:
            input_data.append(0)
            input_data.append(0)
        elif SimAccount.unrealized_pl > 0:
            input_data.append( (SimAccount.unrealized_pl / SimAccount.holding_size) / SimAccount.holding_price)
            input_data.append(0)
        else:
            input_data.append(0)
            input_data.append(-1.0 * (SimAccount.unrealized_pl / SimAccount.holding_size) / SimAccount.holding_price)
        
        #holding period
        if SimAccount.holding_period == 0:
            input_data.append(-1)
        else:
            input_data.append(1.0 / SimAccount.holding_period)
        
        #unrealized pl / holding period
        if SimAccount.holding_period ==0:
            input_data.append(0)
        else:
            input_data.append(SimAccount.unrealized_pl / SimAccount.holding_period)

        return input_data